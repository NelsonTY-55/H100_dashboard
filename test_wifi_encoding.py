#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WiFi 編碼測試腳本
用於測試 WiFi 掃描功能的編碼問題修復
"""

import sys
import logging
from network_utils import NetworkChecker

# 設置日誌
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def test_wifi_functions():
    """測試 WiFi 相關功能"""
    print("=== WiFi 編碼測試 ===")
    
    # 創建網路檢查器
    checker = NetworkChecker()
    
    print("\n1. 測試 WiFi 網路掃描...")
    try:
        networks = checker.scan_wifi_networks()
        print(f"✅ WiFi 掃描成功，找到 {len(networks)} 個網路")
        
        for i, network in enumerate(networks[:3]):  # 只顯示前3個
            print(f"   {i+1}. SSID: {network.get('ssid', 'N/A')}")
            print(f"      信號: {network.get('signal', 'N/A')}")
            print(f"      安全性: {network.get('security', 'N/A')}")
            print(f"      狀態: {network.get('status', 'N/A')}")
            print()
            
    except Exception as e:
        print(f"❌ WiFi 掃描失敗: {e}")
        return False
    
    print("\n2. 測試當前 WiFi 資訊...")
    try:
        current_wifi = checker.get_current_wifi_info()
        if current_wifi:
            print("✅ 當前 WiFi 資訊獲取成功")
            print(f"   SSID: {current_wifi.get('ssid', 'N/A')}")
            print(f"   信號: {current_wifi.get('signal', 'N/A')}")
            print(f"   安全性: {current_wifi.get('security', 'N/A')}")
        else:
            print("⚠️ 當前沒有連接到 WiFi 或無法獲取資訊")
    except Exception as e:
        print(f"❌ 獲取當前 WiFi 資訊失敗: {e}")
        return False
    
    print("\n3. 測試網路狀態...")
    try:
        status = checker.get_network_status()
        print("✅ 網路狀態獲取成功")
        print(f"   網際網路可用: {status.get('internet_available', 'N/A')}")
        print(f"   本地網路可用: {status.get('local_network_available', 'N/A')}")
        print(f"   預設網關: {status.get('default_gateway', 'N/A')}")
        print(f"   平台: {status.get('platform', 'N/A')}")
    except Exception as e:
        print(f"❌ 網路狀態獲取失敗: {e}")
        return False
    
    return True

if __name__ == "__main__":
    print("開始 WiFi 編碼測試...")
    
    try:
        success = test_wifi_functions()
        
        if success:
            print("\n🎉 所有測試通過！編碼問題已修復。")
            sys.exit(0)
        else:
            print("\n❌ 部分測試失敗，請檢查錯誤信息。")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n⚠️ 測試被用戶中斷")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 測試過程中發生未預期的錯誤: {e}")
        sys.exit(1)
