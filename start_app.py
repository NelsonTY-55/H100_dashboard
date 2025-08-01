#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Windows 編碼問題修復腳本
此腳本用於在 Windows 系統上正確啟動 Flask 應用程式，避免編碼問題
"""

import os
import sys
import locale

def setup_encoding():
    """設定正確的編碼環境"""
    try:
        # 設定環境變數強制使用 UTF-8
        os.environ['PYTHONIOENCODING'] = 'utf-8'
        os.environ['LANG'] = 'zh_TW.UTF-8'
        os.environ['LC_ALL'] = 'zh_TW.UTF-8'
        
        # 在 Windows 上設定控制台編碼
        if os.name == 'nt':
            try:
                # 嘗試設定控制台編碼為 UTF-8
                import codecs
                sys.stdout = codecs.getwriter('utf-8')(sys.stdout.detach())
                sys.stderr = codecs.getwriter('utf-8')(sys.stderr.detach())
                sys.stdin = codecs.getreader('utf-8')(sys.stdin.detach())
            except:
                pass
                
        print("編碼環境設定完成")
        print(f"系統編碼: {locale.getpreferredencoding()}")
        print(f"檔案系統編碼: {sys.getfilesystemencoding()}")
        
    except Exception as e:
        print(f"設定編碼時發生錯誤: {e}")
        print("將使用預設編碼")

def main():
    """主要啟動函數"""
    print("=== Flask 應用程式啟動器 ===")
    print("正在設定編碼環境...")
    
    # 設定編碼
    setup_encoding()
    
    print("正在啟動 Flask 應用程式...")
    
    try:
        # 導入並啟動主應用程式
        import app_integrated
        print("應用程式啟動成功！")
    except UnicodeDecodeError as unicode_error:
        print(f"編碼錯誤: {unicode_error}")
        print("嘗試使用替代編碼...")
        
        # 設定替代編碼
        os.environ['PYTHONIOENCODING'] = 'cp950'
        try:
            import app_integrated
            print("使用替代編碼啟動成功！")
        except Exception as fallback_error:
            print(f"替代編碼也失敗: {fallback_error}")
            print("請檢查系統編碼設定")
            
    except Exception as e:
        print(f"啟動應用程式時發生錯誤: {e}")
        print("請檢查相依套件是否已正確安裝")

if __name__ == '__main__':
    main()
