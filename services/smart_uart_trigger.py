"""
智能 UART 觸發管理器
整合 RAS_pi 即時資料服務與本地 UART 掃描系統
"""

import logging
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass

from services.real_time_data_service import (
    get_real_time_service, 
    ScanTriggerEvent, 
    ScanTriggerReason,
    RealTimeDataService
)
from services.raspi_api_client import RaspberryPiConfig


@dataclass
class UARTScanConfig:
    """UART 掃描配置"""
    min_scan_interval: int = 30        # 最小掃描間隔（秒）
    max_scan_interval: int = 300       # 最大掃描間隔（秒）
    adaptive_scanning: bool = True     # 自適應掃描
    priority_mac_ids: List[str] = None # 優先掃描的 MAC IDs
    scan_timeout: int = 60             # 掃描超時（秒）
    
    def __post_init__(self):
        if self.priority_mac_ids is None:
            self.priority_mac_ids = []


class SmartUARTTriggerManager:
    """智能 UART 觸發管理器"""
    
    def __init__(self, 
                 uart_scan_config: UARTScanConfig = None,
                 raspi_config: RaspberryPiConfig = None):
        
        self.scan_config = uart_scan_config or UARTScanConfig()
        self.real_time_service = get_real_time_service(raspi_config)
        self.logger = logging.getLogger(__name__)
        
        # 觸發狀態管理
        self.is_active = False
        self.last_scan_time = None
        self.current_scan_thread = None
        self.scan_in_progress = False
        
        # 掃描統計
        self.stats = {
            'total_scans': 0,
            'successful_scans': 0,
            'failed_scans': 0,
            'triggers_received': 0,
            'triggers_processed': 0,
            'triggers_skipped': 0,
            'average_scan_duration': 0,
            'last_scan_result': None,
            'scan_results_history': []
        }
        
        # 自適應掃描狀態
        self.adaptive_state = {
            'base_interval': self.scan_config.min_scan_interval,
            'current_interval': self.scan_config.min_scan_interval,
            'activity_level': 'normal',  # low, normal, high
            'consecutive_empty_scans': 0,
            'recent_data_activity': False
        }
        
        # UART 控制回調
        self.uart_start_callback = None
        self.uart_stop_callback = None
        self.uart_status_callback = None
        
        # 註冊觸發器回調
        self.real_time_service.add_scan_callback(self._handle_trigger_event)
    
    def set_uart_callbacks(self, 
                          start_callback: Callable[[], bool] = None,
                          stop_callback: Callable[[], bool] = None,
                          status_callback: Callable[[], Dict] = None):
        """設置 UART 控制回調函數"""
        self.uart_start_callback = start_callback
        self.uart_stop_callback = stop_callback
        self.uart_status_callback = status_callback
        self.logger.info("UART 控制回調函數已設置")
    
    def _handle_trigger_event(self, event: ScanTriggerEvent):
        """處理觸發事件"""
        self.stats['triggers_received'] += 1
        
        self.logger.info(f"收到觸發事件: {event.reason.value} - {event.message}")
        
        # 檢查是否應該跳過此次觸發
        if self._should_skip_trigger(event):
            self.stats['triggers_skipped'] += 1
            self.logger.debug(f"跳過觸發事件: {event.reason.value}")
            return
        
        # 處理觸發
        self._process_trigger(event)
        self.stats['triggers_processed'] += 1
    
    def _should_skip_trigger(self, event: ScanTriggerEvent) -> bool:
        """判斷是否應該跳過觸發"""
        now = datetime.now()
        
        # 如果當前有掃描正在進行
        if self.scan_in_progress:
            self.logger.debug("跳過觸發：掃描正在進行中")
            return True
        
        # 檢查最小間隔限制
        if self.last_scan_time:
            time_since_last = (now - self.last_scan_time).total_seconds()
            min_interval = self._get_current_min_interval()
            
            if time_since_last < min_interval:
                # 除非是高優先級觸發
                if event.reason not in [ScanTriggerReason.NEW_MAC_DETECTED, 
                                      ScanTriggerReason.RASPI_RECONNECTED]:
                    self.logger.debug(f"跳過觸發：距離上次掃描僅 {time_since_last:.1f} 秒")
                    return True
        
        # 檢查優先級 MAC IDs
        if (event.reason == ScanTriggerReason.NEW_MAC_DETECTED and 
            self.scan_config.priority_mac_ids and 
            event.mac_ids):
            
            # 如果新檢測到的 MAC 都不在優先列表中，可能跳過
            priority_macs = set(self.scan_config.priority_mac_ids)
            new_macs = set(event.mac_ids)
            
            if not new_macs.intersection(priority_macs):
                # 非優先 MAC，根據活動級別決定
                if self.adaptive_state['activity_level'] == 'low':
                    self.logger.debug("跳過觸發：非優先 MAC 且活動級別低")
                    return True
        
        return False
    
    def _get_current_min_interval(self) -> int:
        """獲取當前最小間隔"""
        if not self.scan_config.adaptive_scanning:
            return self.scan_config.min_scan_interval
        
        # 根據活動級別調整間隔
        base = self.scan_config.min_scan_interval
        
        if self.adaptive_state['activity_level'] == 'high':
            return max(base // 2, 10)  # 高活動：減半，最少10秒
        elif self.adaptive_state['activity_level'] == 'low':
            return min(base * 2, self.scan_config.max_scan_interval // 2)  # 低活動：加倍
        else:
            return base  # 正常活動
    
    def _process_trigger(self, event: ScanTriggerEvent):
        """處理觸發事件"""
        if not self.is_active:
            self.logger.warning("觸發管理器未啟動，忽略觸發事件")
            return
        
        # 根據觸發原因決定掃描策略
        scan_strategy = self._determine_scan_strategy(event)
        
        # 啟動掃描
        self._start_uart_scan(event, scan_strategy)
    
    def _determine_scan_strategy(self, event: ScanTriggerEvent) -> Dict[str, Any]:
        """根據觸發事件決定掃描策略"""
        strategy = {
            'scan_duration': 30,  # 默認掃描時長（秒）
            'priority_mode': False,
            'target_mac_ids': [],
            'scan_type': 'normal'
        }
        
        if event.reason == ScanTriggerReason.NEW_MAC_DETECTED:
            strategy.update({
                'scan_duration': 45,
                'priority_mode': True,
                'target_mac_ids': event.mac_ids,
                'scan_type': 'new_device_focus'
            })
        
        elif event.reason == ScanTriggerReason.DATA_CHANGE_DETECTED:
            strategy.update({
                'scan_duration': 20,
                'scan_type': 'data_sync'
            })
        
        elif event.reason == ScanTriggerReason.RASPI_RECONNECTED:
            strategy.update({
                'scan_duration': 60,
                'priority_mode': True,
                'scan_type': 'full_sync'
            })
        
        elif event.reason == ScanTriggerReason.SCHEDULED_SCAN:
            # 根據當前活動級別調整
            if self.adaptive_state['activity_level'] == 'high':
                strategy['scan_duration'] = 45
            elif self.adaptive_state['activity_level'] == 'low':
                strategy['scan_duration'] = 15
        
        return strategy
    
    def _start_uart_scan(self, event: ScanTriggerEvent, strategy: Dict[str, Any]):
        """啟動 UART 掃描"""
        if self.scan_in_progress:
            self.logger.warning("掃描已在進行中，忽略新的掃描請求")
            return
        
        def scan_worker():
            self.scan_in_progress = True
            scan_start_time = datetime.now()
            
            try:
                self.logger.info(f"開始 UART 掃描 - 觸發原因: {event.reason.value}, 策略: {strategy['scan_type']}")
                
                # 執行 UART 掃描
                scan_result = self._execute_uart_scan(strategy)
                
                # 更新統計
                scan_duration = (datetime.now() - scan_start_time).total_seconds()
                self._update_scan_statistics(scan_result, scan_duration, event)
                
                # 更新自適應狀態
                if self.scan_config.adaptive_scanning:
                    self._update_adaptive_state(scan_result, event)
                
                self.last_scan_time = scan_start_time
                
                self.logger.info(f"UART 掃描完成 - 時長: {scan_duration:.1f}s, 結果: {scan_result.get('status', 'unknown')}")
                
            except Exception as e:
                self.logger.error(f"UART 掃描失敗: {e}")
                self.stats['failed_scans'] += 1
                
            finally:
                self.scan_in_progress = False
        
        # 啟動掃描線程
        self.current_scan_thread = threading.Thread(target=scan_worker, daemon=True)
        self.current_scan_thread.start()
    
    def _execute_uart_scan(self, strategy: Dict[str, Any]) -> Dict[str, Any]:
        """執行實際的 UART 掃描"""
        scan_result = {
            'status': 'started',
            'start_time': datetime.now().isoformat(),
            'strategy': strategy,
            'data_collected': False,
            'error': None
        }
        
        try:
            # 檢查 UART 狀態
            if self.uart_status_callback:
                uart_status = self.uart_status_callback()
                scan_result['uart_status'] = uart_status
                
                # 如果 UART 未運行，嘗試啟動
                if not uart_status.get('is_running', False):
                    if self.uart_start_callback:
                        start_success = self.uart_start_callback()
                        if not start_success:
                            scan_result['status'] = 'failed'
                            scan_result['error'] = 'Failed to start UART'
                            return scan_result
                    else:
                        scan_result['status'] = 'failed'
                        scan_result['error'] = 'No UART start callback available'
                        return scan_result
            
            # 執行掃描（等待指定時間收集資料）
            scan_duration = strategy.get('scan_duration', 30)
            self.logger.info(f"執行 UART 掃描，持續時間: {scan_duration} 秒")
            
            # 這裡可以實現更複雜的掃描邏輯
            # 目前簡單等待掃描時間
            time.sleep(scan_duration)
            
            # 檢查是否收集到資料
            if self.uart_status_callback:
                final_status = self.uart_status_callback()
                scan_result['final_uart_status'] = final_status
                scan_result['data_collected'] = final_status.get('data_count', 0) > 0
            
            scan_result['status'] = 'completed'
            scan_result['end_time'] = datetime.now().isoformat()
            
        except Exception as e:
            scan_result['status'] = 'error'
            scan_result['error'] = str(e)
        
        return scan_result
    
    def _update_scan_statistics(self, scan_result: Dict, duration: float, trigger_event: ScanTriggerEvent):
        """更新掃描統計"""
        self.stats['total_scans'] += 1
        
        if scan_result.get('status') == 'completed':
            self.stats['successful_scans'] += 1
        else:
            self.stats['failed_scans'] += 1
        
        # 更新平均掃描時長
        total_scans = self.stats['total_scans']
        current_avg = self.stats['average_scan_duration']
        self.stats['average_scan_duration'] = (current_avg * (total_scans - 1) + duration) / total_scans
        
        # 記錄最新結果
        self.stats['last_scan_result'] = {
            'timestamp': datetime.now().isoformat(),
            'duration': duration,
            'result': scan_result,
            'trigger': trigger_event.reason.value
        }
        
        # 保持歷史記錄（最多50條）
        self.stats['scan_results_history'].append(self.stats['last_scan_result'])
        if len(self.stats['scan_results_history']) > 50:
            self.stats['scan_results_history'].pop(0)
    
    def _update_adaptive_state(self, scan_result: Dict, trigger_event: ScanTriggerEvent):
        """更新自適應掃描狀態"""
        data_collected = scan_result.get('data_collected', False)
        
        if data_collected:
            self.adaptive_state['consecutive_empty_scans'] = 0
            self.adaptive_state['recent_data_activity'] = True
        else:
            self.adaptive_state['consecutive_empty_scans'] += 1
            
            # 如果連續多次空掃描，降低活動級別
            if self.adaptive_state['consecutive_empty_scans'] >= 3:
                self.adaptive_state['recent_data_activity'] = False
        
        # 更新活動級別
        if trigger_event.reason in [ScanTriggerReason.NEW_MAC_DETECTED, 
                                   ScanTriggerReason.DATA_CHANGE_DETECTED]:
            self.adaptive_state['activity_level'] = 'high'
        elif self.adaptive_state['consecutive_empty_scans'] >= 5:
            self.adaptive_state['activity_level'] = 'low'
        else:
            self.adaptive_state['activity_level'] = 'normal'
        
        self.logger.debug(f"自適應狀態更新: 活動級別={self.adaptive_state['activity_level']}, "
                         f"連續空掃描={self.adaptive_state['consecutive_empty_scans']}")
    
    def start(self) -> bool:
        """啟動觸發管理器"""
        if self.is_active:
            self.logger.warning("智能 UART 觸發管理器已在運行")
            return False
        
        try:
            # 啟動即時資料服務
            if not self.real_time_service.is_running:
                if not self.real_time_service.start():
                    self.logger.error("無法啟動即時資料服務")
                    return False
            
            self.is_active = True
            self.logger.info("智能 UART 觸發管理器已啟動")
            return True
            
        except Exception as e:
            self.logger.error(f"啟動智能 UART 觸發管理器失敗: {e}")
            return False
    
    def stop(self) -> bool:
        """停止觸發管理器"""
        if not self.is_active:
            self.logger.warning("智能 UART 觸發管理器未在運行")
            return False
        
        try:
            self.is_active = False
            
            # 等待當前掃描完成
            if self.current_scan_thread and self.current_scan_thread.is_alive():
                self.logger.info("等待當前掃描完成...")
                self.current_scan_thread.join(timeout=30)
            
            self.logger.info("智能 UART 觸發管理器已停止")
            return True
            
        except Exception as e:
            self.logger.error(f"停止智能 UART 觸發管理器失敗: {e}")
            return False
    
    def get_status(self) -> Dict:
        """獲取觸發管理器狀態"""
        return {
            'active': self.is_active,
            'scan_in_progress': self.scan_in_progress,
            'last_scan_time': self.last_scan_time.isoformat() if self.last_scan_time else None,
            'real_time_service_status': self.real_time_service.get_service_status(),
            'adaptive_state': self.adaptive_state.copy(),
            'scan_config': {
                'min_scan_interval': self.scan_config.min_scan_interval,
                'max_scan_interval': self.scan_config.max_scan_interval,
                'adaptive_scanning': self.scan_config.adaptive_scanning,
                'priority_mac_ids': self.scan_config.priority_mac_ids,
                'scan_timeout': self.scan_config.scan_timeout
            },
            'statistics': self.stats.copy()
        }
    
    def manual_scan(self, message: str = "手動掃描") -> bool:
        """手動觸發掃描"""
        if not self.is_active:
            self.logger.error("觸發管理器未啟動，無法執行手動掃描")
            return False
        
        # 手動觸發即時資料服務
        self.real_time_service.manual_trigger_scan(message)
        return True
    
    def update_scan_config(self, **kwargs):
        """更新掃描配置"""
        updated_fields = []
        
        for key, value in kwargs.items():
            if hasattr(self.scan_config, key):
                setattr(self.scan_config, key, value)
                updated_fields.append(key)
        
        if updated_fields:
            self.logger.info(f"掃描配置已更新: {updated_fields}")
        
        # 同步更新即時資料服務配置
        service_updates = {}
        if 'min_scan_interval' in kwargs:
            service_updates['poll_interval'] = kwargs['min_scan_interval']
        if 'max_scan_interval' in kwargs:
            service_updates['max_scan_interval'] = kwargs['max_scan_interval']
        
        if service_updates:
            self.real_time_service.update_config(**service_updates)


# 全域管理器實例
_trigger_manager = None


def get_trigger_manager(uart_scan_config: UARTScanConfig = None,
                       raspi_config: RaspberryPiConfig = None) -> SmartUARTTriggerManager:
    """獲取智能觸發管理器實例（單例模式）"""
    global _trigger_manager
    if _trigger_manager is None:
        _trigger_manager = SmartUARTTriggerManager(uart_scan_config, raspi_config)
    return _trigger_manager


def cleanup_trigger_manager():
    """清理觸發管理器"""
    global _trigger_manager
    if _trigger_manager and _trigger_manager.is_active:
        _trigger_manager.stop()
    _trigger_manager = None