#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from multi_device_settings import MultiDeviceSettingsManager

def add_device_to_db():
    """重新加入設備到資料庫"""
    
    manager = MultiDeviceSettingsManager()
    
    # 重新加入設備 0013A20042537F54
    test_mac_id = '0013A20042537F54'
    test_settings = {
        'device_name': 'H100 感測器',
        'device_model': 'H100',
        'device_location': '生產線 A',
        'device_description': 'H100 溫濕度感測器',
        'device_type': 'sensor',
        'factory_area': '廠區A',
        'floor_level': '1F'
    }
    
    print(f'重新加入設備 {test_mac_id}...')
    result = manager.save_device_settings(test_mac_id, test_settings)
    print(f'加入結果: {result}')
    
    print('\n目前所有設備:')
    all_devices = manager.load_all_devices()
    for mac, info in all_devices.items():
        device_name = info.get('device_name', '未命名')
        device_model = info.get('device_model', '未知型號')
        print(f'  {mac}: {device_name} ({device_model})')

if __name__ == '__main__':
    add_device_to_db()
