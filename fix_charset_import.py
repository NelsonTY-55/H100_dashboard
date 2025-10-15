#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修正 charset_normalizer 循環導入問題的工具
這個腳本用於解決 Python 環境中 charset_normalizer 與 requests 的相容性問題
"""

import sys
import os
import warnings
import subprocess

def fix_charset_normalizer():
    """修正 charset_normalizer 循環導入問題"""
    print("正在修正 charset_normalizer 循環導入問題...")
    
    # 1. 設置環境變數
    os.environ.setdefault('PYTHONIOENCODING', 'utf-8')
    os.environ.setdefault('PYTHONHASHSEED', '0')
    
    # 2. 忽略相關警告
    warnings.filterwarnings('ignore', category=UserWarning, module='charset_normalizer')
    warnings.filterwarnings('ignore', message='.*charset_normalizer.*')
    
    # 3. 嘗試重新安裝相容版本
    try:
        print("檢查當前 charset_normalizer 版本...")
        import charset_normalizer
        current_version = getattr(charset_normalizer, '__version__', 'unknown')
        print(f"當前版本: {current_version}")
        
        # 如果版本過高，降級到穩定版本
        if current_version.startswith('3.'):
            print("偵測到版本 3.x，建議降級到 2.x 版本以提高相容性")
            print("執行: pip install charset-normalizer==2.1.1")
            
    except ImportError:
        print("charset_normalizer 未安裝")
    except Exception as e:
        print(f"檢查版本時發生錯誤: {e}")
    
    # 4. 測試修正效果
    try:
        print("測試導入...")
        import requests
        print("✓ requests 導入成功")
        
        # 測試基本功能
        print("測試基本 HTTP 功能...")
        response = requests.get('https://httpbin.org/get', timeout=5)
        if response.status_code == 200:
            print("✓ HTTP 請求測試成功")
        else:
            print(f"✗ HTTP 請求測試失敗，狀態碼: {response.status_code}")
            
    except Exception as e:
        print(f"✗ 測試失敗: {e}")
        return False
    
    print("✓ charset_normalizer 問題修正完成")
    return True

def show_fix_instructions():
    """顯示手動修正指示"""
    print("\n=== 手動修正指示 ===")
    print("如果自動修正失敗，請按照以下步驟手動修正：")
    print()
    print("1. 重新安裝相容版本的套件：")
    print("   pip uninstall charset-normalizer requests -y")
    print("   pip install charset-normalizer==2.1.1")
    print("   pip install requests==2.28.2")
    print()
    print("2. 或者使用 conda 安裝：")
    print("   conda install charset-normalizer=2.1.1 requests=2.28.2 -c conda-forge")
    print()
    print("3. 清除 Python 快取：")
    print("   python -Bc \"import sys; [sys.modules.pop(k) for k in list(sys.modules.keys()) if 'charset' in k]\"")
    print()
    print("4. 重新啟動 Python 環境")

if __name__ == "__main__":
    print("=== charset_normalizer 修正工具 ===")
    
    success = fix_charset_normalizer()
    
    if not success:
        show_fix_instructions()
    
    print("\n修正工具執行完成。")