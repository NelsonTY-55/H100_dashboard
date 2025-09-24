"""
設備設定模型
處理設備配置和設定管理
"""

import json
import os
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime


class DeviceSettingsModel:
    """設備設定模型"""
    
    def __init__(self):
        self.current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.device_settings_file = os.path.join(self.current_dir, 'device_settings.json')
        self.multi_device_settings_file = os.path.join(self.current_dir, 'multi_device_settings.json')
    
    def load_device_settings(self) -> Dict[str, Any]:
        """載入設備設定"""
        try:
            if os.path.exists(self.device_settings_file):
                with open(self.device_settings_file, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                return {
                    'success': True,
                    'data': settings
                }
            else:
                return {
                    'success': False,
                    'error': '設備設定文件不存在',
                    'data': {}
                }
        except Exception as e:
            logging.error(f"載入設備設定時發生錯誤: {e}")
            return {
                'success': False,
                'error': str(e),
                'data': {}
            }
    
    def save_device_settings(self, settings: Dict[str, Any]) -> Dict[str, Any]:
        """儲存設備設定"""
        try:
            # 添加時間戳
            settings['last_updated'] = datetime.now().isoformat()
            
            with open(self.device_settings_file, 'w', encoding='utf-8') as f:
                json.dump(settings, f, ensure_ascii=False, indent=2)
            
            return {
                'success': True,
                'message': '設備設定儲存成功'
            }
            
        except Exception as e:
            logging.error(f"儲存設備設定時發生錯誤: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def load_multi_device_settings(self) -> Dict[str, Any]:
        """載入多設備設定"""
        try:
            if os.path.exists(self.multi_device_settings_file):
                with open(self.multi_device_settings_file, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                return {
                    'success': True,
                    'data': settings
                }
            else:
                return {
                    'success': False,
                    'error': '多設備設定文件不存在',
                    'data': {}
                }
        except Exception as e:
            logging.error(f"載入多設備設定時發生錯誤: {e}")
            return {
                'success': False,
                'error': str(e),
                'data': {}
            }
    
    def save_multi_device_settings(self, settings: Dict[str, Any]) -> Dict[str, Any]:
        """儲存多設備設定"""
        try:
            # 添加時間戳
            settings['last_updated'] = datetime.now().isoformat()
            
            with open(self.multi_device_settings_file, 'w', encoding='utf-8') as f:
                json.dump(settings, f, ensure_ascii=False, indent=2)
            
            return {
                'success': True,
                'message': '多設備設定儲存成功'
            }
            
        except Exception as e:
            logging.error(f"儲存多設備設定時發生錯誤: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_device_by_id(self, device_id: str) -> Optional[Dict[str, Any]]:
        """根據設備ID獲取設備資訊"""
        try:
            multi_settings = self.load_multi_device_settings()
            if not multi_settings['success']:
                return None
            
            devices = multi_settings['data'].get('devices', [])
            for device in devices:
                if device.get('id') == device_id:
                    return device
            
            return None
            
        except Exception as e:
            logging.error(f"獲取設備資訊時發生錯誤: {e}")
            return None
    
    def update_device_settings(self, device_id: str, new_settings: Dict[str, Any]) -> Dict[str, Any]:
        """更新指定設備的設定"""
        try:
            multi_settings = self.load_multi_device_settings()
            if not multi_settings['success']:
                return {
                    'success': False,
                    'error': '無法載入多設備設定'
                }
            
            devices = multi_settings['data'].get('devices', [])
            device_found = False
            
            for i, device in enumerate(devices):
                if device.get('id') == device_id:
                    devices[i].update(new_settings)
                    devices[i]['last_updated'] = datetime.now().isoformat()
                    device_found = True
                    break
            
            if not device_found:
                return {
                    'success': False,
                    'error': f'找不到設備 ID: {device_id}'
                }
            
            # 儲存更新後的設定
            save_result = self.save_multi_device_settings(multi_settings['data'])
            return save_result
            
        except Exception as e:
            logging.error(f"更新設備設定時發生錯誤: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def add_device(self, device_info: Dict[str, Any]) -> Dict[str, Any]:
        """新增設備"""
        try:
            multi_settings = self.load_multi_device_settings()
            if not multi_settings['success']:
                # 如果文件不存在，創建新的設定結構
                multi_settings['data'] = {'devices': []}
            
            devices = multi_settings['data'].get('devices', [])
            
            # 檢查設備ID是否已存在
            device_id = device_info.get('id')
            if device_id:
                for device in devices:
                    if device.get('id') == device_id:
                        return {
                            'success': False,
                            'error': f'設備 ID {device_id} 已存在'
                        }
            
            # 添加時間戳
            device_info['created_at'] = datetime.now().isoformat()
            device_info['last_updated'] = datetime.now().isoformat()
            
            devices.append(device_info)
            multi_settings['data']['devices'] = devices
            
            # 儲存設定
            save_result = self.save_multi_device_settings(multi_settings['data'])
            return save_result
            
        except Exception as e:
            logging.error(f"新增設備時發生錯誤: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def remove_device(self, device_id: str) -> Dict[str, Any]:
        """移除設備"""
        try:
            multi_settings = self.load_multi_device_settings()
            if not multi_settings['success']:
                return {
                    'success': False,
                    'error': '無法載入多設備設定'
                }
            
            devices = multi_settings['data'].get('devices', [])
            original_count = len(devices)
            
            # 移除指定的設備
            devices = [device for device in devices if device.get('id') != device_id]
            
            if len(devices) == original_count:
                return {
                    'success': False,
                    'error': f'找不到設備 ID: {device_id}'
                }
            
            multi_settings['data']['devices'] = devices
            
            # 儲存設定
            save_result = self.save_multi_device_settings(multi_settings['data'])
            return save_result
            
        except Exception as e:
            logging.error(f"移除設備時發生錯誤: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_all_devices(self) -> List[Dict[str, Any]]:
        """獲取所有設備列表"""
        try:
            multi_settings = self.load_multi_device_settings()
            if multi_settings['success']:
                return multi_settings['data'].get('devices', [])
            return []
            
        except Exception as e:
            logging.error(f"獲取設備列表時發生錯誤: {e}")
            return []