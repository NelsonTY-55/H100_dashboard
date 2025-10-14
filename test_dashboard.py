#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Dashboard.py 測試腳本
測試 Dashboard API 服務是否能正常啟動
"""

import sys
import os

# 設定路徑
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

def test_dashboard_import():
    """測試 dashboard.py 導入"""
    try:
        print("🧪 測試 dashboard.py 導入...")
        import dashboard
        print("✅ dashboard.py 導入成功")
        return True
    except Exception as e:
        print(f"❌ dashboard.py 導入失敗: {e}")
        return False

def test_dashboard_service():
    """測試 Dashboard API 服務初始化"""
    try:
        print("🧪 測試 Dashboard API 服務初始化...")
        from dashboard import DashboardAPIService
        
        service = DashboardAPIService()
        print("✅ Dashboard API 服務初始化成功")
        
        # 測試路由
        with service.app.test_client() as client:
            response = client.get('/')
            print(f"📡 測試根路由: 狀態碼 {response.status_code}")
            
            response = client.get('/api/health')
            print(f"📡 測試健康檢查: 狀態碼 {response.status_code}")
            
        return True
    except Exception as e:
        print(f"❌ Dashboard API 服務測試失敗: {e}")
        return False

def main():
    """主測試函數"""
    print("=" * 50)
    print("🚀 Dashboard.py 功能測試")
    print("=" * 50)
    
    tests = [
        test_dashboard_import,
        test_dashboard_service
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print()
    
    print("=" * 50)
    print(f"📊 測試結果: {passed}/{total} 通過")
    print("=" * 50)
    
    if passed == total:
        print("🎉 所有測試通過！dashboard.py 可以正常使用")
        return True
    else:
        print("⚠️  部分測試失敗，請檢查錯誤訊息")
        return False

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)