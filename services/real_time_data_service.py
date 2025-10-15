"""
即時資料接收服務
從 RAS_pi 定期拉取最新 UART 資料，並智能觸發本地 UART 掃描
"""

import threading
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field
import queue
from enum import Enum

from services.raspi_api_client import get_raspi_client, get_raspi_aggregator, RaspberryPiConfig


class ScanTriggerReason(Enum):
    """掃描觸發原因"""
    NEW_MAC_DETECTED = "new_mac_detected"
    DATA_CHANGE_DETECTED = "data_change_detected"
    SCHEDULED_SCAN = "scheduled_scan"
    MANUAL_TRIGGER = "manual_trigger"
    RASPI_RECONNECTED = "raspi_reconnected"


@dataclass
class ScanTriggerEvent:
    """掃描觸發事件"""
    reason: ScanTriggerReason
    timestamp: datetime
    mac_ids: List[str] = field(default_factory=list)
    data_summary: Dict[str, Any] = field(default_factory=dict)
    message: str = ""


class RealTimeDataService:
    """即時資料接收服務"""
    
    def __init__(self, raspi_config: RaspberryPiConfig = None):
        self.raspi_config = raspi_config or RaspberryPiConfig()
        self.client = get_raspi_client(self.raspi_config)
        self.aggregator = get_raspi_aggregator()
        self.logger = logging.getLogger(__name__)
        
        # 服務狀態
        self.is_running = False
        self.thread = None
        self.stop_event = threading.Event()
        
        # 資料狀態追蹤
        self.last_known_mac_ids = set()
        self.last_data_summary = {}
        self.last_successful_check = None
        self.connection_lost_time = None
        
        # 觸發器配置
        self.poll_interval = self.raspi_config.poll_interval
        self.max_scan_interval = 300  # 最大掃描間隔（秒）
        self.last_scheduled_scan = None
        
        # 事件處理
        self.trigger_queue = queue.Queue()
        self.scan_callbacks = []
        
        # 統計資訊
        self.stats = {
            'start_time': None,
            'total_checks': 0,
            'successful_checks': 0,
            'connection_errors': 0,
            'triggers_sent': 0,
            'mac_ids_discovered': set(),
            'last_trigger_time': None
        }
    
    def add_scan_callback(self, callback: Callable[[ScanTriggerEvent], None]):
        """添加掃描觸發回調函數"""
        self.scan_callbacks.append(callback)
        self.logger.info(f"已添加掃描回調函數: {callback.__name__}")
    
    def remove_scan_callback(self, callback: Callable[[ScanTriggerEvent], None]):
        """移除掃描觸發回調函數"""
        if callback in self.scan_callbacks:
            self.scan_callbacks.remove(callback)
            self.logger.info(f"已移除掃描回調函數: {callback.__name__}")
    
    def _trigger_scan(self, event: ScanTriggerEvent):
        """觸發掃描事件"""
        try:
            self.trigger_queue.put(event, timeout=1)
            self.stats['triggers_sent'] += 1
            self.stats['last_trigger_time'] = event.timestamp
            
            # 執行回調函數
            for callback in self.scan_callbacks:
                try:
                    callback(event)
                except Exception as e:
                    self.logger.error(f"掃描回調函數執行失敗 {callback.__name__}: {e}")
            
            self.logger.info(f"觸發掃描: {event.reason.value} - {event.message}")
            
        except queue.Full:
            self.logger.warning("觸發隊列已滿，跳過此次觸發")
        except Exception as e:
            self.logger.error(f"觸發掃描時發生錯誤: {e}")
    
    def _check_raspi_data(self) -> bool:
        """檢查 RAS_pi 資料並決定是否觸發掃描"""
        try:
            self.stats['total_checks'] += 1
            
            # 獲取 UART 摘要
            uart_summary = self.aggregator.get_real_time_uart_summary()
            
            if not uart_summary['success']:
                # 連接失敗處理
                if self.client.is_connected:
                    self.connection_lost_time = datetime.now()
                    self.logger.warning("RAS_pi 連接中斷")
                
                self.stats['connection_errors'] += 1
                return False
            
            # 連接恢復處理
            if not self.client.is_connected and self.connection_lost_time:
                self.logger.info("RAS_pi 連接已恢復")
                self._trigger_scan(ScanTriggerEvent(
                    reason=ScanTriggerReason.RASPI_RECONNECTED,
                    timestamp=datetime.now(),
                    message="RAS_pi 連接已恢復，執行同步掃描"
                ))
                self.connection_lost_time = None
            
            self.stats['successful_checks'] += 1
            self.last_successful_check = datetime.now()
            
            # 檢查 UART 狀態
            if not uart_summary['uart_active']:
                self.logger.debug("RAS_pi UART 未啟動，跳過資料檢查")
                return True
            
            # 檢查新的 MAC IDs
            current_mac_ids = set(uart_summary['mac_ids'])
            new_mac_ids = current_mac_ids - self.last_known_mac_ids
            
            if new_mac_ids:
                self.stats['mac_ids_discovered'].update(new_mac_ids)
                self._trigger_scan(ScanTriggerEvent(
                    reason=ScanTriggerReason.NEW_MAC_DETECTED,
                    timestamp=datetime.now(),
                    mac_ids=list(new_mac_ids),
                    message=f"偵測到新的 MAC ID: {', '.join(new_mac_ids)}"
                ))
            
            # 檢查資料變化
            if self._has_significant_data_change(uart_summary):
                self._trigger_scan(ScanTriggerEvent(
                    reason=ScanTriggerReason.DATA_CHANGE_DETECTED,
                    timestamp=datetime.now(),
                    mac_ids=uart_summary['mac_ids'],
                    data_summary=uart_summary['channels_summary'],
                    message=f"偵測到資料變化，共 {uart_summary['recent_data_points']} 個新資料點"
                ))
            
            # 定期掃描檢查
            self._check_scheduled_scan()
            
            # 更新狀態
            self.last_known_mac_ids = current_mac_ids
            self.last_data_summary = uart_summary['channels_summary']
            
            return True
            
        except Exception as e:
            self.logger.error(f"檢查 RAS_pi 資料時發生錯誤: {e}")
            self.stats['connection_errors'] += 1
            return False
    
    def _has_significant_data_change(self, current_summary: Dict) -> bool:
        """檢查是否有顯著的資料變化"""
        if not self.last_data_summary:
            return bool(current_summary.get('recent_data_points', 0) > 0)
        
        current_channels = current_summary.get('channels_summary', {})
        
        # 檢查是否有新的資料點
        current_total_data = current_summary.get('recent_data_points', 0)
        if current_total_data > 10:  # 閾值：10個新資料點
            return True
        
        # 檢查通道數量變化
        for mac_id, channel_info in current_channels.items():
            last_channel_count = self.last_data_summary.get(mac_id, {}).get('channel_count', 0)
            current_channel_count = channel_info.get('channel_count', 0)
            
            if current_channel_count != last_channel_count:
                return True
        
        return False
    
    def _check_scheduled_scan(self):
        """檢查是否需要定期掃描"""
        now = datetime.now()
        
        if self.last_scheduled_scan is None:
            self.last_scheduled_scan = now
            return
        
        time_since_last_scan = now - self.last_scheduled_scan
        
        if time_since_last_scan.total_seconds() >= self.max_scan_interval:
            self._trigger_scan(ScanTriggerEvent(
                reason=ScanTriggerReason.SCHEDULED_SCAN,
                timestamp=now,
                message=f"定期掃描（間隔 {self.max_scan_interval} 秒）"
            ))
            self.last_scheduled_scan = now
    
    def _service_loop(self):
        """服務主循環"""
        self.logger.info(f"即時資料接收服務開始運行，輪詢間隔: {self.poll_interval} 秒")
        
        while not self.stop_event.is_set():
            try:
                self._check_raspi_data()
                
                # 等待下次檢查，支持中斷
                if self.stop_event.wait(timeout=self.poll_interval):
                    break
                    
            except Exception as e:
                self.logger.error(f"服務循環中發生錯誤: {e}")
                # 發生錯誤時等待較短時間後重試
                if self.stop_event.wait(timeout=min(self.poll_interval, 10)):
                    break
        
        self.logger.info("即時資料接收服務已停止")
    
    def start(self) -> bool:
        """啟動服務"""
        if self.is_running:
            self.logger.warning("即時資料接收服務已在運行")
            return False
        
        try:
            # 初始連接測試
            success, health_data = self.client.health_check()
            if not success:
                self.logger.error("無法連接到 RAS_pi，服務啟動失敗")
                return False
            
            self.logger.info(f"RAS_pi 連接成功: {health_data}")
            
            # 重置統計和狀態
            self.stats['start_time'] = datetime.now()
            self.stats['total_checks'] = 0
            self.stats['successful_checks'] = 0
            self.stats['connection_errors'] = 0
            self.stats['triggers_sent'] = 0
            self.stats['mac_ids_discovered'] = set()
            
            # 啟動服務線程
            self.stop_event.clear()
            self.thread = threading.Thread(target=self._service_loop, daemon=True)
            self.thread.start()
            
            self.is_running = True
            self.logger.info("即時資料接收服務已啟動")
            return True
            
        except Exception as e:
            self.logger.error(f"啟動即時資料接收服務失敗: {e}")
            return False
    
    def stop(self) -> bool:
        """停止服務"""
        if not self.is_running:
            self.logger.warning("即時資料接收服務未在運行")
            return False
        
        try:
            self.logger.info("正在停止即時資料接收服務...")
            
            # 設置停止標志
            self.stop_event.set()
            
            # 等待線程結束
            if self.thread and self.thread.is_alive():
                self.thread.join(timeout=10)
                
                if self.thread.is_alive():
                    self.logger.warning("服務線程未在預期時間內停止")
                    return False
            
            self.is_running = False
            self.thread = None
            
            self.logger.info("即時資料接收服務已停止")
            return True
            
        except Exception as e:
            self.logger.error(f"停止即時資料接收服務失敗: {e}")
            return False
    
    def manual_trigger_scan(self, message: str = "手動觸發"):
        """手動觸發掃描"""
        self._trigger_scan(ScanTriggerEvent(
            reason=ScanTriggerReason.MANUAL_TRIGGER,
            timestamp=datetime.now(),
            message=message
        ))
    
    def get_service_status(self) -> Dict:
        """獲取服務狀態"""
        uptime = None
        if self.stats['start_time']:
            uptime = (datetime.now() - self.stats['start_time']).total_seconds()
        
        return {
            'running': self.is_running,
            'uptime_seconds': uptime,
            'raspi_connected': self.client.is_connected,
            'last_successful_check': self.last_successful_check.isoformat() if self.last_successful_check else None,
            'poll_interval': self.poll_interval,
            'stats': {
                'total_checks': self.stats['total_checks'],
                'successful_checks': self.stats['successful_checks'],
                'connection_errors': self.stats['connection_errors'],
                'triggers_sent': self.stats['triggers_sent'],
                'mac_ids_discovered': list(self.stats['mac_ids_discovered']),
                'last_trigger_time': self.stats['last_trigger_time'].isoformat() if self.stats['last_trigger_time'] else None
            },
            'current_state': {
                'known_mac_ids': list(self.last_known_mac_ids),
                'last_data_summary': self.last_data_summary
            },
            'config': {
                'raspi_host': self.raspi_config.host,
                'raspi_port': self.raspi_config.port,
                'max_scan_interval': self.max_scan_interval
            }
        }
    
    def get_pending_triggers(self) -> List[ScanTriggerEvent]:
        """獲取待處理的觸發事件"""
        triggers = []
        while not self.trigger_queue.empty():
            try:
                triggers.append(self.trigger_queue.get_nowait())
            except queue.Empty:
                break
        return triggers
    
    def update_config(self, **kwargs):
        """更新配置"""
        if 'poll_interval' in kwargs:
            self.poll_interval = max(1, kwargs['poll_interval'])
            self.logger.info(f"輪詢間隔已更新為: {self.poll_interval} 秒")
        
        if 'max_scan_interval' in kwargs:
            self.max_scan_interval = max(60, kwargs['max_scan_interval'])
            self.logger.info(f"最大掃描間隔已更新為: {self.max_scan_interval} 秒")


# 全域服務實例
_real_time_service = None


def get_real_time_service(raspi_config: RaspberryPiConfig = None) -> RealTimeDataService:
    """獲取即時資料服務實例（單例模式）"""
    global _real_time_service
    if _real_time_service is None:
        _real_time_service = RealTimeDataService(raspi_config)
    return _real_time_service


def cleanup_real_time_service():
    """清理即時資料服務"""
    global _real_time_service
    if _real_time_service and _real_time_service.is_running:
        _real_time_service.stop()
    _real_time_service = None