#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from datetime import datetime
from multi_device_settings import MultiDeviceSettingsManager

def test_edge_cases():
    """測試可能導致錯誤的邊緣情況"""
    
    manager = MultiDeviceSettingsManager()
    
    print("測試 1: 正常資料")
    normal_settings = {
        'device_name': 'Test Device',
        'device_type': 'sensor',
        'device_model': 'H100'
    }
    result1 = manager.save_device_settings('TEST001', normal_settings)
    print(f"結果: {result1}")
    
    print("\n測試 2: 包含 datetime 物件")
    datetime_settings = {
        'device_name': 'Test Device 2',
        'device_type': 'sensor',
        'device_model': 'H100',
        'installation_date': datetime.now(),
        'last_maintenance': datetime.now()
    }
    result2 = manager.save_device_settings('TEST002', datetime_settings)
    print(f"結果: {result2}")
    
    print("\n測試 3: 包含非字串資料")
    mixed_settings = {
        'device_name': 123,  # 數字
        'device_type': ['sensor'],  # 列表
        'device_model': {'model': 'H100'},  # 字典
        'factory_area': None
    }
    result3 = manager.save_device_settings('TEST003', mixed_settings)
    print(f"結果: {result3}")
    
    print("\n測試 4: 空設定")
    empty_settings = {}
    result4 = manager.save_device_settings('TEST004', empty_settings)
    print(f"結果: {result4}")

if __name__ == '__main__':
    test_edge_cases()
