#!/usr/bin/env python3
# -*- coding: utf-8 -*-

def debug_device_registration():
    """除錯設備註冊問題"""
    
    from multi_device_settings import MultiDeviceSettingsManager
    
    manager = MultiDeviceSettingsManager()
    
    # 測試設備資料
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
    
    # 準備設備資訊字典（同樣的邏輯）
    device_info = {
        'mac_id': test_mac_id,
        'device_name': test_settings.get('device_name', ''),
        'device_type': test_settings.get('device_type', ''),
        'device_model': test_settings.get('device_model', ''),
        'factory_area': test_settings.get('factory_area', ''),
        'floor_level': test_settings.get('floor_level', ''),
        'location_description': test_settings.get('device_location', '') or test_settings.get('device_description', ''),
        'installation_date': test_settings.get('installation_date'),
        'last_maintenance': test_settings.get('last_maintenance'),
        'status': test_settings.get('status', 'active')
    }
    
    print("設備資訊檢查:")
    for key, value in device_info.items():
        print(f"  {key}: {value} (type: {type(value)})")
    
    # 檢查每個值的 SQL 兼容性
    sql_params = (
        device_info.get('mac_id'),
        device_info.get('device_name'),
        device_info.get('device_type'),
        device_info.get('device_model'),
        device_info.get('factory_area'),
        device_info.get('floor_level'),
        device_info.get('location_description'),
        device_info.get('installation_date'),
        device_info.get('last_maintenance'),
        device_info.get('status', 'active'),
        'test_timestamp'
    )
    
    print("\nSQL 參數檢查:")
    for i, param in enumerate(sql_params):
        print(f"  參數 {i}: {param} (type: {type(param)})")
        
    # 測試實際儲存
    print("\n嘗試儲存設備...")
    result = manager.save_device_settings(test_mac_id, test_settings)
    print(f"儲存結果: {result}")

if __name__ == '__main__':
    debug_device_registration()
