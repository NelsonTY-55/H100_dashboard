#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多通訊協定管理器
支援同時啟用多種通訊協定，並提供統一的管理介面
"""

import logging
import threading
import time
from datetime import datetime
from typing import Dict, List, Set, Optional, Tuple
import json

class MultiProtocolManager:
    """多通訊協定管理器"""
    
    def __init__(self, config_manager, protocol_manager):
        self.config_manager = config_manager
        self.protocol_manager = protocol_manager
        self.active_protocols: Set[str] = set()
        self.protocol_status: Dict[str, dict] = {}
        self.lock = threading.Lock()
        
        # 初始化協定狀態
        self._initialize_protocol_status()
    
    def _initialize_protocol_status(self):
        """初始化所有協定的狀態"""
        for protocol in self.config_manager.get_supported_protocols():
            self.protocol_status[protocol] = {
                'name': protocol,
                'description': self.config_manager.get_protocol_description(protocol),
                'is_configured': self.config_manager.is_protocol_configured(protocol),
                'is_running': False,
                'last_activity': None,
                'error_count': 0,
                'last_error': None,
                'start_time': None,
                'data_sent_count': 0,
                'connection_status': 'disconnected'
            }
    
    def get_configured_protocols(self) -> List[str]:
        """獲取所有已設定的協定列表"""
        configured = []
        for protocol in self.config_manager.get_supported_protocols():
            if self.config_manager.is_protocol_configured(protocol):
                configured.append(protocol)
        return configured
    
    def get_available_protocols(self) -> Dict[str, dict]:
        """獲取所有可用協定的詳細資訊"""
        protocols = {}
        for protocol in self.config_manager.get_supported_protocols():
            protocols[protocol] = {
                'name': protocol,
                'description': self.config_manager.get_protocol_description(protocol),
                'is_configured': self.config_manager.is_protocol_configured(protocol),
                'is_running': protocol in self.active_protocols,
                'config': self.config_manager.get_protocol_config(protocol) if self.config_manager.is_protocol_configured(protocol) else None
            }
        return protocols
    
    def start_protocol(self, protocol: str) -> Tuple[bool, str]:
        """啟動指定的協定"""
        try:
            with self.lock:
                # 檢查協定是否支援
                if not self.config_manager.validate_protocol(protocol):
                    return False, f"不支援的協定: {protocol}"
                
                # 檢查協定是否已設定
                if not self.config_manager.is_protocol_configured(protocol):
                    return False, f"{protocol} 協定尚未設定，請先完成設定"
                
                # 檢查協定是否已在運行
                if protocol in self.active_protocols:
                    return True, f"{protocol} 協定已在運行中"
                
                # 啟動協定
                self.protocol_manager.start(protocol)
                self.active_protocols.add(protocol)
                
                # 更新狀態
                self.protocol_status[protocol].update({
                    'is_running': True,
                    'start_time': datetime.now().isoformat(),
                    'connection_status': 'connecting',
                    'last_activity': datetime.now().isoformat()
                })
                
                logging.info(f"多協定管理器：成功啟動 {protocol} 協定")
                return True, f"{protocol} 協定已成功啟動"
                
        except Exception as e:
            error_msg = f"啟動 {protocol} 協定失敗: {str(e)}"
            logging.error(error_msg)
            
            # 更新錯誤狀態
            if protocol in self.protocol_status:
                self.protocol_status[protocol].update({
                    'error_count': self.protocol_status[protocol]['error_count'] + 1,
                    'last_error': error_msg,
                    'connection_status': 'error'
                })
            
            return False, error_msg
    
    def stop_protocol(self, protocol: str) -> Tuple[bool, str]:
        """停止指定的協定"""
        try:
            with self.lock:
                if protocol not in self.active_protocols:
                    return True, f"{protocol} 協定未在運行"
                
                # 停止協定
                self.protocol_manager.stop(protocol)
                self.active_protocols.discard(protocol)
                
                # 更新狀態
                if protocol in self.protocol_status:
                    self.protocol_status[protocol].update({
                        'is_running': False,
                        'connection_status': 'disconnected',
                        'start_time': None
                    })
                
                logging.info(f"多協定管理器：成功停止 {protocol} 協定")
                return True, f"{protocol} 協定已停止"
                
        except Exception as e:
            error_msg = f"停止 {protocol} 協定失敗: {str(e)}"
            logging.error(error_msg)
            return False, error_msg
    
    def start_all_configured(self) -> Dict[str, dict]:
        """啟動所有已設定的協定"""
        results = {}
        configured_protocols = self.get_configured_protocols()
        
        logging.info(f"多協定管理器：準備啟動所有已設定的協定: {configured_protocols}")
        
        for protocol in configured_protocols:
            success, message = self.start_protocol(protocol)
            results[protocol] = {
                'success': success,
                'message': message
            }
            
            # 給每個協定啟動一些時間間隔
            time.sleep(0.5)
        
        return results
    
    def stop_all(self) -> Dict[str, dict]:
        """停止所有運行中的協定"""
        results = {}
        running_protocols = list(self.active_protocols)
        
        logging.info(f"多協定管理器：準備停止所有運行中的協定: {running_protocols}")
        
        for protocol in running_protocols:
            success, message = self.stop_protocol(protocol)
            results[protocol] = {
                'success': success,
                'message': message
            }
        
        return results
    
    def get_status_summary(self) -> dict:
        """獲取所有協定的狀態摘要"""
        with self.lock:
            # 更新運行狀態
            for protocol in self.protocol_status:
                self.protocol_status[protocol]['is_running'] = protocol in self.active_protocols
            
            summary = {
                'total_protocols': len(self.config_manager.get_supported_protocols()),
                'configured_protocols': len(self.get_configured_protocols()),
                'running_protocols': len(self.active_protocols),
                'active_protocol_list': list(self.active_protocols),
                'protocol_details': self.protocol_status.copy(),
                'timestamp': datetime.now().isoformat()
            }
            
            return summary
    
    def update_protocol_activity(self, protocol: str, activity_type: str = 'data_sent'):
        """更新協定活動狀態"""
        if protocol in self.protocol_status:
            with self.lock:
                self.protocol_status[protocol]['last_activity'] = datetime.now().isoformat()
                if activity_type == 'data_sent':
                    self.protocol_status[protocol]['data_sent_count'] += 1
                elif activity_type == 'connected':
                    self.protocol_status[protocol]['connection_status'] = 'connected'
                elif activity_type == 'disconnected':
                    self.protocol_status[protocol]['connection_status'] = 'disconnected'
    
    def get_recommended_protocols(self) -> List[str]:
        """根據當前設定推薦要啟用的協定"""
        configured = self.get_configured_protocols()
        
        # 排除 UART (因為它是數據源，不是傳輸協定)
        recommended = [p for p in configured if p != 'UART']
        
        # 如果沒有其他協定，至少推薦 UART
        if not recommended and 'UART' in configured:
            recommended = ['UART']
        
        return recommended
    
    def auto_start_recommended(self) -> Dict[str, dict]:
        """自動啟動推薦的協定"""
        recommended = self.get_recommended_protocols()
        
        if not recommended:
            return {'message': '沒有找到已設定的協定，請先完成協定設定'}
        
        logging.info(f"多協定管理器：自動啟動推薦協定: {recommended}")
        results = {}
        
        for protocol in recommended:
            success, message = self.start_protocol(protocol)
            results[protocol] = {
                'success': success,
                'message': message
            }
        
        return results
    
    def export_status_report(self) -> str:
        """匯出狀態報告"""
        status = self.get_status_summary()
        
        report = f"""多通訊協定狀態報告
{'='*50}
生成時間: {status['timestamp']}

總覽:
  支援的協定總數: {status['total_protocols']}
  已設定的協定數: {status['configured_protocols']}
  正在運行的協定數: {status['running_protocols']}
  
運行中的協定: {', '.join(status['active_protocol_list']) if status['active_protocol_list'] else '無'}

詳細狀態:
"""
        
        for protocol, details in status['protocol_details'].items():
            report += f"""
  {protocol}:
    描述: {details['description']}
    已設定: {'是' if details['is_configured'] else '否'}
    正在運行: {'是' if details['is_running'] else '否'}
    連接狀態: {details['connection_status']}
    數據傳送次數: {details['data_sent_count']}
    錯誤次數: {details['error_count']}
    最後活動: {details['last_activity'] or '無'}
    最後錯誤: {details['last_error'] or '無'}
"""
        
        return report
