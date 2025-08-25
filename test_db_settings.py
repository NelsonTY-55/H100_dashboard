#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from multi_device_settings import MultiDeviceSettingsManager

def test_database_settings():
    """測試資料庫版本的設備設定管理器"""
    
    # 建立測試實例
    manager = MultiDeviceSettingsManager()
    
    # 測試儲存設備設定
    test_mac_id = '0013A20042537F54'
    test_settings = {
        'device_name': '測試設備',
        'device_model': 'H100',
        'device_location': '測試區域',
        'device_description': '這是一個測試設備',
        'device_type': 'sensor',
        'factory_area': 'A區',
        'floor_level': '1F'
    }
    
    print('測試儲存設備設定...')
    result = manager.save_device_settings(test_mac_id, test_settings)
    print(f'儲存結果: {result}')
    
    print('\n測試載入設備設定...')
    loaded_settings = manager.load_device_settings(test_mac_id)
    print(f'載入的設定: {loaded_settings}')
    
    print('\n測試載入所有設備...')
    all_devices = manager.load_all_devices()
    print(f'所有設備數量: {len(all_devices)}')
    for mac, info in all_devices.items():
        print(f'  {mac}: {info.get("device_name", "未命名")}')
    
    print('\n測試檢查設備是否已設定...')
    is_configured = manager.is_device_configured(test_mac_id)
    print(f'設備 {test_mac_id} 是否已設定: {is_configured}')
    
    print('\n測試取得所有 MAC IDs...')
    mac_ids = manager.get_all_mac_ids()
    print(f'所有 MAC IDs: {mac_ids}')
    
    print('\n測試取得設備數量...')
    device_count = manager.get_device_count()
    print(f'設備數量: {device_count}')

if __name__ == '__main__':
    test_database_settings()
