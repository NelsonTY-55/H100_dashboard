"""
Dashboard API 服務
管理 Dashboard API 服務的核心邏輯和初始化
"""

import os
import sys
import logging
import platform
import time
from datetime import datetime
from flask import Flask
from flask_cors import CORS

# 設定 Python 路徑
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)


class DashboardAPIService:
    """Dashboard API 服務類"""
    
    def __init__(self):
        """初始化 Dashboard API 服務"""
        self.app = None
        self.start_time = time.time()
        self.setup_logging()
        self.setup_app()
        
    def setup_logging(self):
        """設定日誌"""
        log_dir = os.path.join(parent_dir, 'logs')
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
            
        log_file = os.path.join(log_dir, f'dashboard_api_{datetime.now().strftime("%Y%m%d")}.log')
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file, encoding='utf-8'),
                logging.StreamHandler(sys.stdout)
            ]
        )
        
        self.logger = logging.getLogger(__name__)
        self.logger.info("Dashboard API 服務日誌系統初始化完成")
        
    def setup_app(self):
        """設定 Flask 應用程式"""
        self.app = Flask(__name__)
        self.app.config['SECRET_KEY'] = 'dashboard-api-secret-key-2024'
        
        # 啟用 CORS 支援
        CORS(self.app, resources={
            r"/api/*": {
                "origins": "*",
                "methods": ["GET", "POST", "PUT", "DELETE"],
                "allow_headers": "*"
            }
        })
        
        # 註冊控制器
        self.register_controllers()
        
    def register_controllers(self):
        """註冊控制器"""
        try:
            # 導入並註冊 Dashboard API 控制器
            from controllers.dashboard_api_controller import dashboard_api_bp
            self.app.register_blueprint(dashboard_api_bp)
            self.logger.info("Dashboard API 控制器註冊成功")
            
        except ImportError as e:
            self.logger.error(f"無法導入控制器: {e}")
            # 如果無法導入控制器，設定基本路由
            self.setup_basic_routes()
            
    def setup_basic_routes(self):
        """設定基本路由（當控制器無法載入時）"""
        @self.app.route('/')
        def index():
            return {
                'service': 'H100 Dashboard API',
                'status': 'running (basic mode)',
                'message': '控制器載入失敗，運行在基本模式',
                'timestamp': datetime.now().isoformat()
            }
            
        @self.app.route('/api/health')
        def health():
            return {
                'status': 'healthy',
                'service': 'dashboard-api',
                'mode': 'basic',
                'timestamp': datetime.now().isoformat()
            }
    
    def get_service_info(self):
        """取得服務資訊"""
        uptime_seconds = time.time() - self.start_time
        return {
            'service_name': 'H100 Dashboard API',
            'version': '1.0.0',
            'uptime_seconds': uptime_seconds,
            'uptime_formatted': f"{uptime_seconds:.2f} 秒",
            'platform': platform.system(),
            'python_version': platform.python_version(),
            'start_time': datetime.fromtimestamp(self.start_time).isoformat()
        }
    
    def run(self, host='0.0.0.0', port=5001, debug=False):
        """啟動 API 服務"""
        print("=" * 60)
        print("🚀 H100 Dashboard API 服務啟動中...")
        print("=" * 60)
        print(f"📍 服務位址: http://{host}:{port}")
        print(f"🕒 啟動時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"🖥️  運行平台: {platform.system()} {platform.version()}")
        print(f"🐍 Python 版本: {platform.python_version()}")
        print()
        print("🔗 可用的 API 端點:")
        print(f"   ├─ 服務首頁: http://{host}:{port}/")
        print(f"   ├─ 健康檢查: http://{host}:{port}/api/health")
        print(f"   ├─ 系統資訊: http://{host}:{port}/api/system")
        print(f"   ├─ 儀表板資料: http://{host}:{port}/api/dashboard")
        print(f"   ├─ 設定資訊: http://{host}:{port}/api/config")
        print(f"   └─ 服務狀態: http://{host}:{port}/api/status")
        print()
        print("=" * 60)
        print("🎯 API 服務已就緒，按 Ctrl+C 停止服務")
        print("=" * 60)
        
        try:
            self.app.run(
                host=host,
                port=port,
                debug=debug,
                threaded=True,
                use_reloader=False
            )
        except KeyboardInterrupt:
            print("\n\n⏹️  收到停止信號，正在關閉服務...")
            self.logger.info("Dashboard API 服務正常關閉")
        except Exception as e:
            print(f"\n❌ 服務運行錯誤: {e}")
            self.logger.error(f"Dashboard API 服務運行錯誤: {e}")


def create_dashboard_api_app():
    """工廠函數：創建 Dashboard API 應用程式"""
    service = DashboardAPIService()
    return service.app