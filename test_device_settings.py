#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
設備設定測試腳本
用於測試設備設定的儲存和載入功能
"""

import os
import sys
import json
from device_settings import DeviceSettingsManager

def test_device_settings():
    """測試設備設定功能"""
    print("=== 設備設定測試 ===")
    
    # 建立設備設定管理器
    manager = DeviceSettingsManager()
    
    print(f"設定檔案路徑: {manager.config_file}")
    print(f"設定檔案是否存在: {os.path.exists(manager.config_file)}")
    
    # 測試載入設定
    print("\n1. 測試載入設定...")
    settings = manager.load_settings()
    print(f"載入的設定: {json.dumps(settings, ensure_ascii=False, indent=2)}")
    print(f"是否已設定: {manager.is_configured()}")
    
    # 測試儲存設定
    print("\n2. 測試儲存設定...")
    test_settings = {
        'device_name': '測試設備',
        'device_location': '測試位置',
        'device_model': '測試型號',
        'device_serial': 'TEST123',
        'device_description': '這是一個測試設備'
    }
    
    success = manager.save_settings(test_settings)
    print(f"儲存結果: {'成功' if success else '失敗'}")
    
    if success:
        # 重新載入確認
        print("\n3. 重新載入確認...")
        reloaded_settings = manager.load_settings()
        print(f"重新載入的設定: {json.dumps(reloaded_settings, ensure_ascii=False, indent=2)}")
        print(f"是否已設定: {manager.is_configured()}")
        
        # 檢查檔案內容
        print(f"\n4. 檢查檔案內容...")
        if os.path.exists(manager.config_file):
            with open(manager.config_file, 'r', encoding='utf-8') as f:
                file_content = f.read()
                print(f"檔案大小: {len(file_content)} 字元")
                print(f"檔案內容預覽:\n{file_content[:200]}...")
        else:
            print("設定檔案不存在！")
    
    return success

def clean_test_settings():
    """清理測試設定"""
    manager = DeviceSettingsManager()
    if os.path.exists(manager.config_file):
        try:
            os.remove(manager.config_file)
            print(f"已清理測試設定檔案: {manager.config_file}")
        except Exception as e:
            print(f"清理測試設定時發生錯誤: {e}")

if __name__ == '__main__':
    print("當前工作目錄:", os.getcwd())
    print("腳本目錄:", os.path.dirname(os.path.abspath(__file__)))
    
    # 執行測試
    test_result = test_device_settings()
    
    # 詢問是否清理測試設定
    if test_result:
        response = input("\n是否要清理測試設定？(y/N): ")
        if response.lower() == 'y':
            clean_test_settings()
    
    print("\n測試完成！")
