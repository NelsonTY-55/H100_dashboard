# Multi-Device Settings Manager
# 多設備設定管理模組

import json
import os
from datetime import datetime
from database_manager import DatabaseManager

class MultiDeviceSettingsManager:
    def __init__(self, config_file='multi_device_settings.json'):
        """
        初始化多設備設定管理器
        現在使用資料庫儲存設備設定
        
        Args:
            config_file (str): 保留參數以維持兼容性，但不再使用
        """
        self.config_file = config_file  # 保留以維持兼容性
        self.db_manager = DatabaseManager()
        self.default_device_settings = {
            'device_name': '',
            'device_location': '',  # 對應 location_description
            'device_model': '',
            'device_serial': '',  # 這是 MAC ID
            'device_description': '',  # 對應 location_description
            'created_at': None,
            'updated_at': None
        }
        
    def load_all_devices(self):
        """
        載入所有設備設定
        從資料庫載入所有設備資訊
        
        Returns:
            dict: MAC ID 為 key 的設備設定字典
        """
        try:
            devices_info = self.db_manager.get_device_info()
            devices = {}
            
            for device in devices_info:
                mac_id = device.get('mac_id')
                if mac_id:
                    devices[mac_id] = {
                        'device_name': device.get('device_name', ''),
                        'device_location': device.get('location_description', ''),
                        'device_model': device.get('device_model', ''),
                        'device_serial': mac_id,
                        'device_description': device.get('location_description', ''),
                        'device_type': device.get('device_type', ''),
                        'factory_area': device.get('factory_area', ''),
                        'floor_level': device.get('floor_level', ''),
                        'installation_date': device.get('installation_date', ''),
                        'last_maintenance': device.get('last_maintenance', ''),
                        'status': device.get('status', 'active'),
                        'created_at': device.get('created_at'),
                        'updated_at': device.get('updated_at')
                    }
            
            return devices
            
        except Exception as e:
            print(f"載入多設備設定時發生錯誤: {e}")
            return {}
    
    def load_device_settings(self, mac_id):
        """
        載入特定設備的設定
        從資料庫載入指定 MAC ID 的設備資訊
        
        Args:
            mac_id (str): 設備的 MAC ID
            
        Returns:
            dict: 設備設定字典
        """
        try:
            device_info = self.db_manager.get_device_info(mac_id)
            
            if device_info and len(device_info) > 0:
                device = device_info[0]  # 取得第一個結果
                device_settings = {
                    'device_name': device.get('device_name', ''),
                    'device_location': device.get('location_description', ''),
                    'device_model': device.get('device_model', ''),
                    'device_serial': mac_id,
                    'device_description': device.get('location_description', ''),
                    'device_type': device.get('device_type', ''),
                    'factory_area': device.get('factory_area', ''),
                    'floor_level': device.get('floor_level', ''),
                    'installation_date': device.get('installation_date', ''),
                    'last_maintenance': device.get('last_maintenance', ''),
                    'status': device.get('status', 'active'),
                    'created_at': device.get('created_at'),
                    'updated_at': device.get('updated_at')
                }
                
                # 確保所有必要的欄位都存在
                for key, value in self.default_device_settings.items():
                    if key not in device_settings:
                        device_settings[key] = value
                        
                return device_settings
            else:
                # 如果設備不存在，返回預設設定但設定正確的 MAC ID
                default_settings = self.default_device_settings.copy()
                default_settings['device_serial'] = mac_id
                return default_settings
                
        except Exception as e:
            print(f"載入設備 {mac_id} 設定時發生錯誤: {e}")
            # 如果發生錯誤，返回預設設定但設定正確的 MAC ID
            default_settings = self.default_device_settings.copy()
            default_settings['device_serial'] = mac_id
            return default_settings
    
    def save_device_settings(self, mac_id, settings):
        """
        儲存特定設備的設定
        儲存設備資訊到資料庫
        
        Args:
            mac_id (str): 設備的 MAC ID
            settings (dict): 要儲存的設定字典
            
        Returns:
            bool: 儲存是否成功
        """
        try:
            # 確保資料類型正確
            def safe_str(value):
                """安全地轉換為字串，保持 None 值"""
                if value is None:
                    return None
                elif isinstance(value, str):
                    return value
                else:
                    return str(value)
            
            # 準備設備資訊字典
            device_info = {
                'mac_id': safe_str(mac_id),
                'device_name': safe_str(settings.get('device_name', '')),
                'device_type': safe_str(settings.get('device_type', '')),
                'device_model': safe_str(settings.get('device_model', '')),
                'factory_area': safe_str(settings.get('factory_area', '')),
                'floor_level': safe_str(settings.get('floor_level', '')),
                'location_description': safe_str(settings.get('device_location', '') or settings.get('device_description', '')),
                'installation_date': settings.get('installation_date'),  # 讓 register_device 處理類型轉換
                'last_maintenance': settings.get('last_maintenance'),    # 讓 register_device 處理類型轉換
                'status': safe_str(settings.get('status', 'active'))
            }
            
            # 使用資料庫管理器儲存設備資訊
            success = self.db_manager.register_device(device_info)
            
            if success:
                print(f"設備 {mac_id} 的設定已儲存到資料庫")
            else:
                print(f"儲存設備 {mac_id} 設定時發生錯誤")
                
            return success
            
        except Exception as e:
            print(f"儲存設備 {mac_id} 設定時發生錯誤: {e}")
            return False
    
    def delete_device_settings(self, mac_id):
        """
        刪除特定設備的設定
        從資料庫中刪除指定的設備資訊
        
        Args:
            mac_id (str): 設備的 MAC ID
            
        Returns:
            bool: 刪除是否成功
        """
        try:
            success = self.db_manager.delete_device(mac_id)
            
            if success:
                print(f"設備 {mac_id} 的設定已從資料庫刪除")
            else:
                print(f"設備 {mac_id} 不存在於資料庫中或刪除失敗")
                
            return success
                
        except Exception as e:
            print(f"刪除設備 {mac_id} 設定時發生錯誤: {e}")
            return False
    
    def get_device_count(self):
        """
        取得設備數量
        
        Returns:
            int: 設備數量
        """
        return len(self.load_all_devices())
    
    def get_all_mac_ids(self):
        """
        取得所有設備的 MAC ID 列表
        
        Returns:
            list: MAC ID 列表
        """
        return list(self.load_all_devices().keys())
    
    def is_device_configured(self, mac_id):
        """
        檢查特定設備是否已設定
        
        Args:
            mac_id (str): 設備的 MAC ID
            
        Returns:
            bool: 是否已設定設備名稱
        """
        device_settings = self.load_device_settings(mac_id)
        return bool(device_settings.get('device_name', '').strip())
    
    def reset_all_settings(self):
        """
        重設所有設備設定
        從資料庫中刪除所有設備資訊
        
        Returns:
            bool: 重設是否成功
        """
        try:
            import sqlite3
            with sqlite3.connect(self.db_manager.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM device_info')
                conn.commit()
            
            print("所有設備設定已從資料庫重設")
            return True
            
        except Exception as e:
            print(f"重設所有設定時發生錯誤: {e}")
            return False
    
    def export_settings(self, export_file=None):
        """
        匯出所有設備設定
        
        Args:
            export_file (str): 匯出檔案路徑，如果不指定則使用預設命名
            
        Returns:
            str: 匯出檔案路徑
        """
        if not export_file:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            export_file = f"device_settings_export_{timestamp}.json"
        
        try:
            all_devices = self.load_all_devices()
            export_data = {
                'export_time': datetime.now().isoformat(),
                'device_count': len(all_devices),
                'devices': all_devices
            }
            
            with open(export_file, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2)
            
            print(f"設備設定已匯出到 {export_file}")
            return export_file
            
        except Exception as e:
            print(f"匯出設備設定時發生錯誤: {e}")
            return None

# 建立全域實例
multi_device_settings_manager = MultiDeviceSettingsManager()
