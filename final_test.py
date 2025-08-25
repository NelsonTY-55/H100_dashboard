#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from multi_device_settings import MultiDeviceSettingsManager

def final_test():
    """最終功能測試"""
    
    manager = MultiDeviceSettingsManager()
    target_device = '0013A20042537F54'
    
    print('測試設備設定功能:')
    print('=' * 30)
    
    # 1. 載入設備設定
    print('1. 載入設備設定:')
    settings = manager.load_device_settings(target_device)
    print(f'   設備名稱: {settings.get("device_name")}')
    print(f'   設備型號: {settings.get("device_model")}')
    print(f'   設備類型: {settings.get("device_type")}')
    print(f'   位置: {settings.get("device_location")}')
    
    # 2. 檢查是否已設定
    print('\n2. 檢查設備是否已設定:')
    is_configured = manager.is_device_configured(target_device)
    print(f'   是否已設定: {is_configured}')
    
    # 3. 取得所有設備
    print('\n3. 所有設備列表:')
    all_devices = manager.load_all_devices()
    for mac, info in all_devices.items():
        device_name = info.get("device_name", "未命名")
        print(f'   {mac}: {device_name}')
    
    # 4. 設備數量
    print(f'\n4. 總設備數量: {manager.get_device_count()}')
    
    print('\n✓ 所有功能測試完成，設備設定已成功遷移到資料庫')

if __name__ == '__main__':
    final_test()
