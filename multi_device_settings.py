# Multi-Device Settings Manager
# 多設備設定管理模組

import json
import os
from datetime import datetime

class MultiDeviceSettingsManager:
    def __init__(self, config_file='multi_device_settings.json'):
        """
        初始化多設備設定管理器
        
        Args:
            config_file (str): 設定檔案路徑
        """
        self.config_file = config_file
        self.default_device_settings = {
            'device_name': '',
            'device_location': '',
            'device_model': '',
            'device_serial': '',  # 這是 MAC ID
            'device_description': '',
            'created_at': None,
            'updated_at': None
        }
        
    def load_all_devices(self):
        """
        載入所有設備設定
        
        Returns:
            dict: MAC ID 為 key 的設備設定字典
        """
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    devices = json.load(f)
                    return devices if isinstance(devices, dict) else {}
            else:
                return {}
        except Exception as e:
            print(f"載入多設備設定時發生錯誤: {e}")
            return {}
    
    def load_device_settings(self, mac_id):
        """
        載入特定設備的設定
        
        Args:
            mac_id (str): 設備的 MAC ID
            
        Returns:
            dict: 設備設定字典
        """
        all_devices = self.load_all_devices()
        if mac_id in all_devices:
            device_settings = all_devices[mac_id].copy()
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
    
    def save_device_settings(self, mac_id, settings):
        """
        儲存特定設備的設定
        
        Args:
            mac_id (str): 設備的 MAC ID
            settings (dict): 要儲存的設定字典
            
        Returns:
            bool: 儲存是否成功
        """
        try:
            # 載入所有設備設定
            all_devices = self.load_all_devices()
            
            # 添加時間戳記
            current_time = datetime.now().isoformat()
            
            # 如果設備已存在，保留 created_at
            if mac_id in all_devices and all_devices[mac_id].get('created_at'):
                settings['created_at'] = all_devices[mac_id]['created_at']
            else:
                settings['created_at'] = current_time
            
            settings['updated_at'] = current_time
            settings['device_serial'] = mac_id  # 確保 MAC ID 正確
            
            # 更新設備設定
            all_devices[mac_id] = settings
            
            # 儲存到檔案
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(all_devices, f, ensure_ascii=False, indent=2)
            
            print(f"設備 {mac_id} 的設定已儲存到 {self.config_file}")
            return True
            
        except Exception as e:
            print(f"儲存設備 {mac_id} 設定時發生錯誤: {e}")
            return False
    
    def delete_device_settings(self, mac_id):
        """
        刪除特定設備的設定
        
        Args:
            mac_id (str): 設備的 MAC ID
            
        Returns:
            bool: 刪除是否成功
        """
        try:
            all_devices = self.load_all_devices()
            if mac_id in all_devices:
                del all_devices[mac_id]
                
                # 儲存更新後的設定
                with open(self.config_file, 'w', encoding='utf-8') as f:
                    json.dump(all_devices, f, ensure_ascii=False, indent=2)
                
                print(f"設備 {mac_id} 的設定已刪除")
                return True
            else:
                print(f"設備 {mac_id} 不存在")
                return False
                
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
        
        Returns:
            bool: 重設是否成功
        """
        try:
            if os.path.exists(self.config_file):
                os.remove(self.config_file)
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
