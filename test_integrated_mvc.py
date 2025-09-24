# test_integrated_mvc.py
"""
測試 app_integrated.py MVC 重構版本的功能
"""

import sys
import os
import logging
from datetime import datetime

# 設定路徑
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

def test_imports():
    """測試所有模組導入"""
    print("🧪 測試模組導入...")
    
    try:
        # 測試模型導入
        from models.logging_model import LoggingModel, DailyLogHandler
        from models.ftp_model import FTPModel, LocalFTPServer
        from models.dashboard_data_sender_model import DashboardDataSenderModel, DashboardDataSender
        print("   ✅ 模型層模組導入成功")
        
        # 測試控制器導入
        from controllers.integrated_home_controller import integrated_home_bp
        from controllers.integrated_device_controller import integrated_device_bp
        from controllers.integrated_wifi_controller import integrated_wifi_bp
        from controllers.integrated_dashboard_controller import integrated_dashboard_bp
        from controllers.integrated_protocol_controller import integrated_protocol_bp
        from controllers.integrated_uart_controller import integrated_uart_bp
        print("   ✅ 控制器層模組導入成功")
        
        # 測試應用程式工廠
        from app_factory import create_app
        print("   ✅ 應用程式工廠導入成功")
        
        return True
        
    except ImportError as e:
        print(f"   ❌ 模組導入失敗: {e}")
        return False


def test_models():
    """測試模型功能"""
    print("\n🧪 測試模型功能...")
    
    try:
        # 測試日誌模型
        from models.logging_model import LoggingModel
        logging_model = LoggingModel()
        print("   ✅ 日誌模型初始化成功")
        
        # 測試 FTP 模型
        from models.ftp_model import FTPModel
        ftp_model = FTPModel()
        status = ftp_model.get_local_server_status()
        print(f"   ✅ FTP 模型初始化成功，狀態: {status['is_running']}")
        
        # 測試 Dashboard 資料發送模型
        from models.dashboard_data_sender_model import DashboardDataSenderModel
        sender_model = DashboardDataSenderModel()
        sender_status = sender_model.get_sender_status()
        print(f"   ✅ Dashboard 發送模型初始化成功，啟用: {sender_status['enabled']}")
        
        return True
        
    except Exception as e:
        print(f"   ❌ 模型測試失敗: {e}")
        return False


def test_controllers():
    """測試控制器功能"""
    print("\n🧪 測試控制器功能...")
    
    try:
        # 測試 Blueprint 創建
        from controllers.integrated_home_controller import integrated_home_bp
        from controllers.integrated_device_controller import integrated_device_bp
        from controllers.integrated_wifi_controller import integrated_wifi_bp
        from controllers.integrated_dashboard_controller import integrated_dashboard_bp
        from controllers.integrated_protocol_controller import integrated_protocol_bp
        from controllers.integrated_uart_controller import integrated_uart_bp
        
        blueprints = [
            ('integrated_home', integrated_home_bp),
            ('integrated_device', integrated_device_bp),
            ('integrated_wifi', integrated_wifi_bp),
            ('integrated_dashboard', integrated_dashboard_bp),
            ('integrated_protocol', integrated_protocol_bp),
            ('integrated_uart', integrated_uart_bp),
        ]
        
        for name, bp in blueprints:
            if bp and hasattr(bp, 'name'):
                print(f"   ✅ {name} Blueprint 創建成功")
            else:
                print(f"   ❌ {name} Blueprint 創建失敗")
                return False
        
        return True
        
    except Exception as e:
        print(f"   ❌ 控制器測試失敗: {e}")
        return False


def test_app_factory():
    """測試應用程式工廠"""
    print("\n🧪 測試應用程式工廠...")
    
    try:
        from app_factory import create_app
        
        # 創建測試應用程式
        test_config = {
            'TESTING': True,
            'DEBUG': False,
            'HOST': '127.0.0.1',
            'PORT': 5555
        }
        
        app = create_app(test_config)
        
        if app:
            print("   ✅ Flask 應用程式創建成功")
            print(f"   📋 應用程式名稱: {app.name}")
            print(f"   📋 偵錯模式: {app.config.get('DEBUG')}")
            print(f"   📋 測試模式: {app.config.get('TESTING')}")
            
            # 檢查路由
            with app.app_context():
                routes = []
                for rule in app.url_map.iter_rules():
                    routes.append(str(rule))
                
                print(f"   📋 註冊的路由數量: {len(routes)}")
                if len(routes) > 0:
                    print("   📋 部分路由:")
                    for route in routes[:5]:  # 只顯示前5個路由
                        print(f"      - {route}")
            
            return True
        else:
            print("   ❌ Flask 應用程式創建失敗")
            return False
            
    except Exception as e:
        print(f"   ❌ 應用程式工廠測試失敗: {e}")
        return False


def test_app_integrated_mvc():
    """測試整合應用程式"""
    print("\n🧪 測試整合應用程式...")
    
    try:
        # 測試主程式導入
        import app_integrated_mvc
        
        if hasattr(app_integrated_mvc, 'create_dashboard_app'):
            print("   ✅ create_dashboard_app 函數存在")
        
        if hasattr(app_integrated_mvc, 'initialize_components'):
            print("   ✅ initialize_components 函數存在")
        
        if hasattr(app_integrated_mvc, 'main'):
            print("   ✅ main 函數存在")
        
        # 不實際啟動應用程式，只測試創建
        print("   ℹ️  跳過實際應用程式啟動（避免端口衝突）")
        
        return True
        
    except Exception as e:
        print(f"   ❌ 整合應用程式測試失敗: {e}")
        return False


def main():
    """主測試函數"""
    print("=" * 60)
    print("🔍 H100 Dashboard MVC 重構版功能測試")
    print("=" * 60)
    print(f"⏰ 測試時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📁 工作目錄: {os.getcwd()}")
    
    test_results = []
    
    # 執行所有測試
    tests = [
        ("模組導入測試", test_imports),
        ("模型功能測試", test_models),
        ("控制器功能測試", test_controllers),
        ("應用程式工廠測試", test_app_factory),
        ("整合應用程式測試", test_app_integrated_mvc),
    ]
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            test_results.append((test_name, result))
        except Exception as e:
            print(f"   💥 {test_name} 執行異常: {e}")
            test_results.append((test_name, False))
    
    # 測試結果摘要
    print("\n" + "=" * 60)
    print("📊 測試結果摘要")
    print("=" * 60)
    
    passed = 0
    total = len(test_results)
    
    for test_name, result in test_results:
        status = "✅ 通過" if result else "❌ 失敗"
        print(f"{status} {test_name}")
        if result:
            passed += 1
    
    print(f"\n📈 通過率: {passed}/{total} ({(passed/total*100):.1f}%)")
    
    if passed == total:
        print("🎉 所有測試通過！MVC 重構成功！")
        return True
    else:
        print("⚠️  部分測試失敗，請檢查錯誤訊息")
        return False


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)