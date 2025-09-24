"""
H100 Dashboard 主應用程式
使用 MVC 架構重構的 Flask 儀表板應用程式
"""

import os
import sys
import logging
from app_factory import create_app, initialize_services

# 添加當前目錄到 Python 路徑
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# 修復 charset_normalizer 循環導入問題
if 'charset_normalizer' in sys.modules:
    del sys.modules['charset_normalizer']

# 嘗試導入外部依賴
try:
    import requests
    requests_available = True
except (ImportError, AttributeError) as e:
    print(f"requests 導入錯誤: {e}")
    requests_available = False

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    print("psutil 未安裝，系統監控功能將受限，可以執行 'pip install psutil' 來安裝")

# 應用程式配置
app_config = {
    'DEBUG': True,
    'HOST': '0.0.0.0',
    'PORT': 5001,
    'SECRET_KEY': 'dashboard_secret_key_2025',
    'TEMPLATES_AUTO_RELOAD': True,
    'JSON_AS_ASCII': False,
    'ENABLE_CORS': False,
    'PSUTIL_AVAILABLE': PSUTIL_AVAILABLE,
    'REQUESTS_AVAILABLE': requests_available
}

def create_dashboard_app():
    """創建儀表板應用程式"""
    try:
        # 創建 Flask 應用程式
        app = create_app(app_config)
        
        # 初始化服務
        initialize_services(app)
        
        return app
        
    except Exception as e:
        print(f"創建應用程式時發生錯誤: {e}")
        raise

def main():
    """主函數"""
    try:
        print("正在啟動 H100 Dashboard...")
        print("=" * 50)
        
        # 創建應用程式
        app = create_dashboard_app()
        
        # 顯示啟動資訊
        print("✅ H100 Dashboard 初始化完成")
        print("\n📊 支援的功能:")
        print(f"  - 系統監控: {'✅' if PSUTIL_AVAILABLE else '❌'}")
        print(f"  - 網路請求: {'✅' if requests_available else '❌'}")
        print(f"  - UART 數據: ✅")
        print(f"  - 設備管理: ✅")
        print(f"  - WiFi 管理: ✅")
        
        print("\n🌐 可用的路由:")
        print("  - 儀表板主頁: http://localhost:5001/dashboard")
        print("  - 設備設定: http://localhost:5001/db-setting")
        print("  - 數據分析: http://localhost:5001/data-analysis")
        print("  - API 健康檢查: http://localhost:5001/api/health")
        print("  - API 狀態: http://localhost:5001/api/status")
        print("  - UART API: http://localhost:5001/api/uart/*")
        print("  - 網路 API: http://localhost:5001/api/wifi/*")
        
        print("\n🔧 系統資訊:")
        print(f"  - 除錯模式: {'開啟' if app.config['DEBUG'] else '關閉'}")
        print(f"  - 主機: {app.config['HOST']}")
        print(f"  - 端口: {app.config['PORT']}")
        
        print("\n" + "=" * 50)
        print("🚀 正在啟動伺服器...")
        
        # 啟動應用程式
        app.run(
            debug=app.config['DEBUG'],
            host=app.config['HOST'],
            port=app.config['PORT'],
            threaded=True
        )
        
    except KeyboardInterrupt:
        print("\n\n⏹️  收到中斷信號，正在關閉伺服器...")
        
    except Exception as e:
        print(f"\n❌ 啟動 H100 Dashboard 時發生錯誤: {e}")
        print("\n🔍 請檢查:")
        print("1. 端口 5001 是否被其他程式佔用")
        print("2. 相依套件是否已正確安裝")
        print("3. 必要的檔案和目錄是否存在")
        print("4. Python 版本是否相容 (建議 Python 3.8+)")
        
        # 顯示詳細錯誤資訊（僅在除錯模式下）
        if app_config.get('DEBUG', False):
            import traceback
            print("\n📋 詳細錯誤資訊:")
            traceback.print_exc()
        
        sys.exit(1)

if __name__ == '__main__':
    main()