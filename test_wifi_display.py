#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WiFi 狀態顯示測試
測試當前WiFi連接狀態的顯示功能
"""

import requests
import json
import sys

def test_wifi_current_api():
    """測試WiFi當前狀態API"""
    print("=== WiFi 當前狀態測試 ===")
    
    try:
        # 假設應用程式運行在本地端口5000
        url = "http://localhost:5000/api/wifi/current"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            print("✅ API 調用成功")
            print(f"📄 回應資料: {json.dumps(data, indent=2, ensure_ascii=False)}")
            
            if data.get('success') and data.get('current_wifi'):
                wifi = data['current_wifi']
                print("\n📶 WiFi 連接資訊:")
                print(f"   網路名稱 (SSID): {wifi.get('ssid', 'N/A')}")
                print(f"   信號強度: {wifi.get('signal', 'N/A')}")
                print(f"   安全性: {wifi.get('security', 'N/A')}")
                print(f"   狀態: {wifi.get('status', 'N/A')}")
                
                # 模擬前端顯示格式
                signal_text = f" ({wifi['signal']})" if wifi.get('signal') else ''
                display_text = f"已連接: {wifi['ssid']}{signal_text}"
                print(f"\n🖥️  前端顯示格式: {display_text}")
                
            elif data.get('success'):
                print("\n⚠️  目前沒有連接到WiFi網路")
            else:
                print(f"\n❌ API 返回錯誤: {data.get('message', '未知錯誤')}")
                
        else:
            print(f"❌ HTTP 錯誤: {response.status_code}")
            print(f"   回應內容: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("❌ 無法連接到應用程式，請確認服務是否運行在 http://localhost:5000")
    except requests.exceptions.Timeout:
        print("❌ 請求超時")
    except Exception as e:
        print(f"❌ 測試失敗: {e}")

def test_wifi_scan_api():
    """測試WiFi掃描API"""
    print("\n=== WiFi 掃描測試 ===")
    
    try:
        url = "http://localhost:5000/api/wifi/scan"
        response = requests.get(url, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            print("✅ WiFi 掃描 API 調用成功")
            
            if data.get('success'):
                networks = data.get('networks', [])
                print(f"📶 找到 {len(networks)} 個WiFi網路:")
                
                for i, network in enumerate(networks[:5], 1):  # 只顯示前5個
                    ssid = network.get('ssid', 'N/A')
                    signal = network.get('signal', 'N/A')
                    security = network.get('security', 'N/A')
                    status = network.get('status', 'N/A')
                    
                    print(f"   {i}. {ssid}")
                    print(f"      信號: {signal} | 安全性: {security} | 狀態: {status}")
                
                if len(networks) > 5:
                    print(f"   ... 還有 {len(networks) - 5} 個網路")
                    
            else:
                print(f"❌ WiFi 掃描失敗: {data.get('message', '未知錯誤')}")
                
        else:
            print(f"❌ HTTP 錯誤: {response.status_code}")
            
    except Exception as e:
        print(f"❌ WiFi 掃描測試失敗: {e}")

if __name__ == "__main__":
    print("WiFi 狀態顯示功能測試")
    print("=" * 40)
    
    test_wifi_current_api()
    test_wifi_scan_api()
    
    print("\n📋 測試完成")
    print("\n💡 提示:")
    print("   - 如果看到連接錯誤，請先啟動應用程式: python app_integrated.py")
    print("   - 如果WiFi資訊顯示不正確，請檢查網路連接和WiFi適配器狀態")
    print("   - 前端頁面會定期更新WiFi狀態，每15秒刷新一次")
