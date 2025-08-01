#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
多頻道設備型號功能測試
測試前端和後端對多頻道設備型號的支援
"""

import json
import requests
import sys
import os

def test_multi_channel_device_model():
    """測試多頻道設備型號功能"""
    
    print("=" * 60)
    print("多頻道設備型號功能測試")
    print("=" * 60)
    
    # 測試數據
    test_settings = {
        "device_name": "測試設備-多頻道",
        "device_location": "測試廠房",
        "device_model": {
            "1": "Model-A1",
            "2": "Model-B2", 
            "3": "Model-C3",
            "4": "Model-D4"
        },
        "device_serial": "AA:BB:CC:DD:EE:FF",
        "device_description": "這是多頻道設備型號測試"
    }
    
    base_url = "http://127.0.0.1:5000"
    
    try:
        # 1. 測試保存多頻道設備型號
        print("1. 測試保存多頻道設備型號...")
        response = requests.post(
            f"{base_url}/api/device-settings",
            json=test_settings,
            headers={'Content-Type': 'application/json'}
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                print("✓ 多頻道設備型號保存成功")
                print(f"  回應: {data.get('message')}")
            else:
                print("✗ 保存失敗:", data.get('message'))
                return False
        else:
            print(f"✗ HTTP錯誤: {response.status_code}")
            return False
        
        # 2. 測試載入多頻道設備型號
        print("\n2. 測試載入多頻道設備型號...")
        response = requests.get(f"{base_url}/api/device-settings")
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                settings = data.get('settings', {})
                device_model = settings.get('device_model', {})
                
                print("✓ 設備型號載入成功")
                print("  載入的設備型號:")
                
                if isinstance(device_model, dict):
                    for channel, model in device_model.items():
                        print(f"    頻道 {channel}: {model}")
                    
                    # 驗證數據完整性
                    expected_models = test_settings['device_model']
                    if device_model == expected_models:
                        print("✓ 設備型號數據完整且正確")
                    else:
                        print("✗ 設備型號數據不匹配")
                        print(f"  期望: {expected_models}")
                        print(f"  實際: {device_model}")
                        return False
                else:
                    print(f"✗ 設備型號格式錯誤: {type(device_model)} - {device_model}")
                    return False
            else:
                print("✗ 載入失敗:", data.get('message'))
                return False
        else:
            print(f"✗ HTTP錯誤: {response.status_code}")
            return False
        
        # 3. 測試多設備API
        print("\n3. 測試多設備API...")
        mac_id = test_settings['device_serial']
        response = requests.get(f"{base_url}/api/device-settings?mac_id={mac_id}")
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                settings = data.get('settings', {})
                device_model = settings.get('device_model', {})
                
                print("✓ 多設備API載入成功")
                print(f"  MAC ID: {data.get('mac_id')}")
                print("  設備型號:")
                
                if isinstance(device_model, dict):
                    for channel, model in device_model.items():
                        print(f"    頻道 {channel}: {model}")
                else:
                    print(f"✗ 設備型號格式錯誤: {type(device_model)}")
                    return False
            else:
                print("✗ 多設備API載入失敗:", data.get('message'))
                return False
        else:
            print(f"✗ HTTP錯誤: {response.status_code}")
            return False
        
        # 4. 測試設備列表API
        print("\n4. 測試設備列表API...")
        response = requests.get(f"{base_url}/api/dashboard/devices")
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                devices = data.get('devices', [])
                print(f"✓ 設備列表API成功，找到 {len(devices)} 個設備")
                
                # 尋找測試設備
                test_device = None
                for device in devices:
                    if device.get('mac_id') == mac_id:
                        test_device = device
                        break
                
                if test_device:
                    device_model = test_device.get('device_model', {})
                    print(f"  測試設備: {test_device.get('device_name')}")
                    print("  設備型號:")
                    
                    if isinstance(device_model, dict):
                        for channel, model in device_model.items():
                            print(f"    頻道 {channel}: {model}")
                    else:
                        print(f"  注意: 設備型號格式為 {type(device_model)}: {device_model}")
                else:
                    print(f"  注意: 在設備列表中未找到MAC ID為 {mac_id} 的設備")
                    print("  這可能是因為UART數據源不可用，但不影響設定功能")
            else:
                print("✗ 設備列表API失敗:", data.get('message'))
                # 不返回False，因為UART可能未運行
        else:
            print(f"✗ HTTP錯誤: {response.status_code}")
            # 不返回False，因為UART可能未運行
        
        print("\n" + "=" * 60)
        print("✓ 多頻道設備型號功能測試完成")
        print("✓ 所有核心功能正常運作")
        print("=" * 60)
        return True
        
    except requests.ConnectionError:
        print("✗ 無法連接到伺服器")
        print("  請確認Flask應用程式正在運行 (python app_integrated.py)")
        return False
    except Exception as e:
        print(f"✗ 測試過程中發生錯誤: {e}")
        return False

def test_backward_compatibility():
    """測試向後相容性"""
    
    print("\n" + "=" * 60)
    print("向後相容性測試")
    print("=" * 60)
    
    # 測試舊格式的設備型號 (字串格式)
    old_format_settings = {
        "device_name": "舊格式測試設備",
        "device_location": "測試廠房",
        "device_model": "Old-Model-String",  # 舊格式：字串
        "device_serial": "11:22:33:44:55:66",
        "device_description": "向後相容性測試"
    }
    
    base_url = "http://127.0.0.1:5000"
    
    try:
        # 保存舊格式設定
        print("1. 測試保存舊格式設備型號...")
        response = requests.post(
            f"{base_url}/api/device-settings",
            json=old_format_settings,
            headers={'Content-Type': 'application/json'}
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                print("✓ 舊格式設備型號保存成功")
            else:
                print("✗ 保存失敗:", data.get('message'))
                return False
        else:
            print(f"✗ HTTP錯誤: {response.status_code}")
            return False
        
        # 載入並檢查是否正確轉換
        print("\n2. 測試載入並檢查格式轉換...")
        response = requests.get(f"{base_url}/api/device-settings")
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                settings = data.get('settings', {})
                device_model = settings.get('device_model', {})
                
                print("✓ 設定載入成功")
                
                if isinstance(device_model, dict):
                    print("✓ 舊格式已正確轉換為新格式")
                    print("  轉換後的設備型號:")
                    for channel, model in device_model.items():
                        print(f"    頻道 {channel}: {model}")
                    
                    # 檢查頻道1是否包含原始型號
                    if device_model.get('1') == old_format_settings['device_model']:
                        print("✓ 原始型號正確保存在頻道1")
                    else:
                        print("✗ 原始型號未正確保存")
                        return False
                else:
                    print(f"✗ 格式轉換失敗，仍為: {type(device_model)}")
                    return False
            else:
                print("✗ 載入失敗:", data.get('message'))
                return False
        else:
            print(f"✗ HTTP錯誤: {response.status_code}")
            return False
        
        print("\n" + "=" * 60)
        print("✓ 向後相容性測試完成")
        print("✓ 舊格式正確轉換為新格式")
        print("=" * 60)
        return True
        
    except Exception as e:
        print(f"✗ 向後相容性測試失敗: {e}")
        return False

if __name__ == "__main__":
    print("開始多頻道設備型號功能測試...\n")
    
    # 執行主要功能測試
    success1 = test_multi_channel_device_model()
    
    # 執行向後相容性測試
    success2 = test_backward_compatibility()
    
    if success1 and success2:
        print("\n🎉 所有測試通過！")
        print("多頻道設備型號功能已成功實現")
        sys.exit(0)
    else:
        print("\n❌ 部分測試失敗")
        print("請檢查錯誤訊息並修正問題")
        sys.exit(1)
