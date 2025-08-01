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
        # 使用絕對路徑確保設定檔案在正確位置
        if not os.path.isabs(config_file):
            # 如果是相對路徑，將其放在腳本目錄下
            script_dir = os.path.dirname(os.path.abspath(__file__))
            self.config_file = os.path.join(script_dir, config_file)
        else:
            self.config_file = config_file
        
        self.default_device = {
            'device_name': '',
            'device_location': '',
            'device_model': {
                '0': '',
                '1': '',
                '2': '',
                '3': '',
                '4': '',
                '5': '',
                '6': ''
            },
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
            
            # 處理舊版本的 device_model 格式相容性
            if isinstance(device_settings.get('device_model'), str):
                old_model = device_settings['device_model']
                device_settings['device_model'] = {
                    '0': old_model,
                    '1': '',
                    '2': '',
                    '3': '',
                    '4': '',
                    '5': '',
                    '6': ''
                }
            elif not isinstance(device_settings.get('device_model'), dict):
                device_settings['device_model'] = self.default_device['device_model'].copy()
            
            # 確保所有必要的欄位都存在
            for key, value in self.default_device.items():
                if key not in device_settings:
                    device_settings[key] = value
            return device_settings
        else:
            # 如果設備不存在，返回預設設定但設定正確的 MAC ID
            default_settings = self.default_device.copy()
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
            existing_device = all_devices.get(mac_id, {})
            
            # 如果是第一次建立，設定 created_at
            if not existing_device.get('created_at'):
                settings['created_at'] = current_time
            else:
                settings['created_at'] = existing_device['created_at']
            
            settings['updated_at'] = current_time
            settings['device_serial'] = mac_id  # 確保 MAC ID 正確
            
            # 更新設備設定
            all_devices[mac_id] = settings
            
            # 儲存到檔案
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(all_devices, f, ensure_ascii=False, indent=2)
            
            return True
        except Exception as e:
            print(f"儲存設備設定時發生錯誤: {e}")
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
                # 儲存到檔案
                with open(self.config_file, 'w', encoding='utf-8') as f:
                    json.dump(all_devices, f, ensure_ascii=False, indent=2)
                return True
            return False
        except Exception as e:
            print(f"刪除設備設定時發生錯誤: {e}")
            return False
    
    def get_all_device_list(self):
        """
        獲取所有設備的基本資訊列表
        
        Returns:
            list: 設備資訊列表
        """
        all_devices = self.load_all_devices()
        device_list = []
        
        for mac_id, settings in all_devices.items():
            device_info = {
                'mac_id': mac_id,
                'device_name': settings.get('device_name', '未命名設備'),
                'device_location': settings.get('device_location', ''),
                'device_model': settings.get('device_model', {}),
                'device_description': settings.get('device_description', ''),
                'created_at': settings.get('created_at'),
                'updated_at': settings.get('updated_at')
            }
            device_list.append(device_info)
        
        # 按更新時間排序（最新的在前）
        device_list.sort(key=lambda x: x.get('updated_at', ''), reverse=True)
        return device_list
    
    def device_exists(self, mac_id):
        """
        檢查設備是否存在
        
        Args:
            mac_id (str): 設備的 MAC ID
            
        Returns:
            bool: 設備是否存在
        """
        all_devices = self.load_all_devices()
        return mac_id in all_devices
    
    def get_device_count(self):
        """
        獲取設備數量
        
        Returns:
            int: 設備數量
        """
        all_devices = self.load_all_devices()
        return len(all_devices)
