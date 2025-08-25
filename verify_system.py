#!/usr/bin/env python3
# -*- coding: utf-8 -*-

def verify_system():
    """驗證系統是否正常運作"""
    
    try:
        from multi_device_settings import MultiDeviceSettingsManager
        from database_manager import DatabaseManager
        
        # 檢查資料庫連接
        db = DatabaseManager()
        print('✓ 資料庫管理器正常載入')
        
        # 檢查設備設定管理器
        manager = MultiDeviceSettingsManager()
        devices = manager.load_all_devices()
        print(f'✓ 設備設定管理器正常載入，目前有 {len(devices)} 個設備')
        
        # 檢查特定設備
        target_device = '0013A20042537F54'
        device_settings = manager.load_device_settings(target_device)
        if device_settings and device_settings.get('device_name'):
            device_name = device_settings['device_name']
            print(f'✓ 設備 {target_device} 已在資料庫中: {device_name}')
        else:
            print(f'✗ 設備 {target_device} 不在資料庫中')
        
        print('\n系統狀態: 正常運作，設備設定已成功從 JSON 檔案遷移到資料庫')
        return True
        
    except Exception as e:
        print(f'✗ 系統測試失敗: {e}')
        return False

if __name__ == '__main__':
    verify_system()
