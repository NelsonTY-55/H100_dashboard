#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
測試 database_manager 的 get_statistics 方法
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database_manager import DatabaseManager
import json

def test_get_statistics():
    """測試 get_statistics 方法的所有調用方式"""
    print("=== 測試 get_statistics 方法 ===")
    
    try:
        dm = DatabaseManager()
        print("✅ DatabaseManager 實例化成功")
        
        # 測試 1: 無參數調用
        print("\n測試 1: 無參數調用")
        result1 = dm.get_statistics()
        print(f"✅ 成功，返回 {len(str(result1))} 字符")
        
        # 測試 2: 空字典參數
        print("\n測試 2: 空字典參數")
        result2 = dm.get_statistics({})
        print(f"✅ 成功，返回 {len(str(result2))} 字符")
        
        # 測試 3: 包含篩選條件的字典
        print("\n測試 3: 包含篩選條件的字典")
        filters = {'factory_area': '廠區A'}
        result3 = dm.get_statistics(filters)
        print(f"✅ 成功，返回 {len(str(result3))} 字符")
        print(f"   篩選結果: {json.dumps(result3, ensure_ascii=False, indent=2)}")
        
        # 測試 4: 錯誤的調用方式（應該失敗）
        print("\n測試 4: 錯誤的調用方式（應該失敗）")
        try:
            result4 = dm.get_statistics(factory_area='廠區A')
            print("❌ 意外成功了")
        except TypeError as e:
            print(f"✅ 預期的錯誤: {e}")
            
        print("\n=== 所有測試完成 ===")
        
    except Exception as e:
        print(f"❌ 測試失敗: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_get_statistics()
