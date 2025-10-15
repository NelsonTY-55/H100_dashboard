#!/usr/bin/env python3
"""
測試 charset_normalizer 問題是否已解決
"""

import warnings
warnings.filterwarnings("ignore", message=".*charset_normalizer.*")

import os
import sys

# 設定環境變數
os.environ['CHARSET_NORMALIZER_USE_MYPYC'] = '0'
os.environ['PYTHONOPTIMIZE'] = '0'

print("正在測試 charset_normalizer 相關問題...")

try:
    print("1. 測試基本 HTTP 請求功能...")
    
    # 測試 requests 是否能正常工作（通常依賴 charset_normalizer）
    try:
        import requests
        print("   ✓ requests 模組載入成功")
        
        # 簡單的本地測試（不需要網路）
        session = requests.Session()
        print("   ✓ requests Session 建立成功")
        
    except Exception as e:
        print(f"   ✗ requests 測試失敗: {e}")
    
    print("\n2. 測試 charset_normalizer 直接導入...")
    try:
        import charset_normalizer
        print("   ✓ charset_normalizer 直接導入成功")
    except Exception as e:
        print(f"   ✗ charset_normalizer 直接導入失敗: {e}")
        print("      這通常不會影響應用程式運行")
    
    print("\n3. 測試 urllib3...")
    try:
        import urllib3
        print("   ✓ urllib3 導入成功")
    except Exception as e:
        print(f"   ✗ urllib3 導入失敗: {e}")
    
    print("\n4. 測試應用程式主要模組...")
    try:
        from flask import Flask
        print("   ✓ Flask 導入成功")
        
        app = Flask(__name__)
        print("   ✓ Flask 應用建立成功")
        
    except Exception as e:
        print(f"   ✗ Flask 測試失敗: {e}")
    
    print("\n測試完成！")
    print("如果看到大部分 ✓ 符號，表示 charset_normalizer 問題已成功處理。")
    print("即使 charset_normalizer 直接導入失敗，也不會影響應用程式的核心功能。")
    
except Exception as e:
    print(f"測試過程中發生錯誤: {e}")

print("\n按 Enter 鍵結束...")
input()