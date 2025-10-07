#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import requests
import logging

def trigger_device_sync():
    """觸發現有設備設定的同步"""
    try:
        # 讀取現有的設備設定
        with open('multi_device_settings.json', 'r', encoding='utf-8') as f:
            device_settings = json.load(f)
        
        print(f"找到 {len(device_settings)} 個現有設備設定")
        
        for mac_id, settings in device_settings.items():
            print(f"\n觸發設備 {mac_id} 的同步...")
            print(f"  設備名稱: {settings.get('device_name', 'N/A')}")
            print(f"  設備位置: {settings.get('device_location', 'N/A')}")
            
            # 發送 POST 請求來觸發設備設定的儲存（進而觸發同步）
            url = 'http://localhost:5001/api/device-settings'
            
            try:
                response = requests.post(url, json=settings, timeout=10)
                result = response.json()
                
                if result.get('success'):
                    print(f"  ✅ 同步成功: {result.get('message', '')}")
                else:
                    print(f"  ❌ 同步失敗: {result.get('message', '')}")
                    
            except Exception as e:
                print(f"  ❌ 請求失敗: {e}")
        
        print(f"\n🎉 已嘗試同步所有 {len(device_settings)} 個設備")
        
    except Exception as e:
        print(f"❌ 觸發同步失敗: {e}")

def check_database_after_sync():
    """檢查同步後的資料庫狀態"""
    print("\n=== 檢查資料庫同步結果 ===")
    
    try:
        # 檢查廠區 API
        response = requests.get('http://localhost:5001/api/database/factory-areas', timeout=10)
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                print(f"✅ 廠區列表: {result.get('data', [])}")
            else:
                print(f"❌ 廠區 API 錯誤: {result.get('message', '')}")
        else:
            print(f"❌ 廠區 API 請求失敗，狀態碼: {response.status_code}")
        
        # 檢查樓層 API
        response = requests.get('http://localhost:5001/api/database/floor-levels', timeout=10)
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                print(f"✅ 樓層列表: {result.get('data', [])}")
            else:
                print(f"❌ 樓層 API 錯誤: {result.get('message', '')}")
        else:
            print(f"❌ 樓層 API 請求失敗，狀態碼: {response.status_code}")
        
        # 檢查 MAC ID API
        response = requests.get('http://localhost:5001/api/database/mac-ids', timeout=10)
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                print(f"✅ MAC ID 列表: {result.get('data', [])}")
            else:
                print(f"❌ MAC ID API 錯誤: {result.get('message', '')}")
        else:
            print(f"❌ MAC ID API 請求失敗，狀態碼: {response.status_code}")
            
    except Exception as e:
        print(f"❌ 檢查資料庫失敗: {e}")

if __name__ == '__main__':
    print("🔄 開始觸發設備設定同步...")
    trigger_device_sync()
    
    print("\n⏳ 等待同步完成...")
    import time
    time.sleep(2)
    
    check_database_after_sync()
    print("\n✅ 同步測試完成！")
