#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
設備設定除錯工具
用於檢查和修復設備設定問題
"""

import os
import json
from device_settings import DeviceSettingsManager

def debug_device_settings():
    """除錯設備設定"""
    print("=== 設備設定除錯工具 ===")
    print(f"當前工作目錄: {os.getcwd()}")
    
    # 創建設備設定管理器
    manager = DeviceSettingsManager()
    print(f"設定檔案路徑: {manager.config_file}")
    print(f"設定檔案存在: {os.path.exists(manager.config_file)}")
    
    # 檢查當前設定
    print("\n1. 檢查當前設定...")
    settings = manager.load_settings()
    print("當前設定內容:")
    for key, value in settings.items():
        print(f"  {key}: {value}")
    
    print(f"\n2. is_configured() 結果: {manager.is_configured()}")
    
    # 如果沒有設定，創建一個測試設定
    if not manager.is_configured():
        print("\n3. 設備未設定，創建測試設定...")
        test_settings = {
            'device_name': 'DB測試設備',
            'device_location': '測試環境',
            'device_model': 'Test Model v2',
            'device_serial': 'TEST-MAC-001',
            'device_description': '這是一個用於測試的設備設定'
        }
        
        print("準備儲存的測試設定:")
        for key, value in test_settings.items():
            print(f"  {key}: {value}")
        
        success = manager.save_settings(test_settings)
        print(f"\n儲存結果: {'成功' if success else '失敗'}")
        
        if success:
            # 重新檢查
            print("\n4. 重新檢查設定...")
            new_settings = manager.load_settings()
            print("重新載入的設定:")
            for key, value in new_settings.items():
                print(f"  {key}: {value}")
            print(f"is_configured() 結果: {manager.is_configured()}")
            
            # 檢查檔案內容
            if os.path.exists(manager.config_file):
                print(f"\n5. 檔案內容檢查:")
                file_stats = os.stat(manager.config_file)
                print(f"  檔案大小: {file_stats.st_size} bytes")
                
                with open(manager.config_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    print(f"  檔案內容:\n{content}")
        else:
            print("設定儲存失敗，請檢查權限或路徑問題")
    else:
        print("\n3. 設備已設定，檢查設定有效性...")
        device_name = settings.get('device_name', '')
        print(f"  設備名稱: '{device_name}'")
        print(f"  設備名稱長度: {len(device_name)}")
        print(f"  設備名稱去空白後: '{device_name.strip()}'")
        print(f"  去空白後長度: {len(device_name.strip())}")

def test_api_endpoint():
    """測試 API 端點"""
    print("\n=== API 端點測試 ===")
    try:
        import requests
        
        # 測試 GET
        print("測試 GET /api/device-settings...")
        response = requests.get('http://127.0.0.1:5000/api/device-settings')
        print(f"狀態碼: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"回應內容: {json.dumps(data, ensure_ascii=False, indent=2)}")
        else:
            print(f"錯誤回應: {response.text}")
            
    except ImportError:
        print("requests 模組未安裝，跳過 API 測試")
    except Exception as e:
        print(f"API 測試失敗: {e}")

if __name__ == '__main__':
    debug_device_settings()
    
    response = input("\n是否要測試 API 端點? (y/N): ")
    if response.lower() == 'y':
        test_api_endpoint()
    
    print("\n除錯完成！")
