#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Dashboard API 服務 - MVC 架構重構版本
獨立的 Dashboard 和設備設定管理 API 服務

重構特點：
- 使用 MVC 架構
- 模組化設計
- 改善錯誤處理  
- 優化性能
- 統一配置管理
"""

from __future__ import annotations  # 啟用延遲型別註解評估

# === 修正 charset_normalizer 循環導入問題 ===
import sys
import warnings
import os

# 在導入其他模組前，先設置環境變數避免 charset_normalizer 問題
os.environ.setdefault('PYTHONIOENCODING', 'utf-8')

# 暫時忽略 charset_normalizer 相關的警告
warnings.filterwarnings('ignore', category=UserWarning, module='charset_normalizer')

# 嘗試修正 charset_normalizer 問題
try:
    # 清理可能的問題模組
    charset_mod_keys = [k for k in sys.modules.keys() if 'charset' in k.lower()]
    for key in charset_mod_keys:
        if key in sys.modules:
            del sys.modules[key]
    
    import charset_normalizer
    # 強制初始化 charset_normalizer
    getattr(charset_normalizer, '__version__', None)
except (ImportError, AttributeError) as e:
    print(f"Warning: charset_normalizer issue ignored: {e}")
    pass

import logging
from pathlib import Path
from flask import Flask

# 添加專案根目錄到 Python 路徑
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# === 配置和常數 ===
class DashboardConfig:
    """Dashboard 配置管理"""
    
    # 基本配置
    SECRET_KEY = 'dashboard_secret_key_2025'
    HOST = '0.0.0.0'
    PORT = 5001
    DEBUG = os.getenv('DEBUG', 'True').lower() == 'true'
    
    # 樹莓派配置
    RASPBERRY_PI_HOST = os.getenv('RASPBERRY_PI_HOST', '192.168.113.239')
    RASPBERRY_PI_PORT = int(os.getenv('RASPBERRY_PI_PORT', '5000'))
    
    # 模式配置
    STANDALONE_MODE = os.getenv('DASHBOARD_STANDALONE_MODE', 'True').lower() == 'true'
    
    # 性能配置
    API_CACHE_TTL = 60  # API快取TTL (秒)
    DATA_CACHE_TTL = 300  # 數據快取TTL (秒)
    MAX_CACHE_SIZE = 200
    
    # 請求配置
    REQUEST_TIMEOUT = 10
    MAX_RETRIES = 3

config = DashboardConfig()

# === 日誌設定 ===
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] [Dashboard-MVC] %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('dashboard_mvc.log', encoding='utf-8')
    ]
)

logger = logging.getLogger(__name__)

# === 安全導入管理器 ===
class SafeImportManager:
    """安全導入管理器，處理可選依賴的導入"""
    
    def __init__(self):
        self.available_modules = {}
        self.failed_imports = {}
    
    def safe_import(self, module_name: str, fallback=None, required: bool = False):
        """安全導入模組"""
        if module_name in self.available_modules:
            return self.available_modules[module_name]
        
        if module_name in self.failed_imports:
            if required:
                raise ImportError(f"Required module '{module_name}' is not available")
            return fallback
        
        try:
            module = __import__(module_name)
            self.available_modules[module_name] = module
            logger.info(f"Successfully imported {module_name}")
            return module
            
        except (ImportError, AttributeError) as e:
            self.failed_imports[module_name] = str(e)
            error_msg = f"Failed to import {module_name}: {e}"
            
            # 對於 charset_normalizer 或其他非關鍵模組，提供友好訊息
            if module_name in ['charset_normalizer', 'urllib3', 'certifi', 'requests', 'idna']:
                error_msg += " (這是非關鍵依賴，不影響核心功能)"
            
            logger.warning(error_msg)
            
            if required:
                raise ImportError(f"Required module '{module_name}' is not available: {e}")
            
            return fallback
    
    def is_available(self, module_name: str) -> bool:
        """檢查模組是否可用"""
        return module_name in self.available_modules

# 創建導入管理器實例
import_manager = SafeImportManager()

# === 核心模組導入 ===
try:
    from config.config_manager import ConfigManager
    from network_utils import network_checker, create_offline_mode_manager
    from device_settings import DeviceSettingsManager
    from multi_device_settings import MultiDeviceSettingsManager
    logger.info("核心模組導入成功")
except ImportError as e:
    logger.error(f"核心模組導入失敗: {e}")
    raise

# === 可選模組導入 ===
requests = import_manager.safe_import('requests')
psutil = import_manager.safe_import('psutil')

# === 資料庫模組導入 ===
try:
    from database_manager import db_manager
    DATABASE_AVAILABLE = True
    logger.info("資料庫管理器載入成功")
except ImportError as e:
    logger.error(f"資料庫管理器載入失敗: {e}")
    DATABASE_AVAILABLE = False
    db_manager = None

# === Flask 應用初始化 ===
def create_app() -> Flask:
    """創建並配置 Flask 應用"""
    app = Flask(__name__)
    app.secret_key = config.SECRET_KEY
    
    # 配置 Flask
    app.config.update({
        'JSON_AS_ASCII': False,
        'JSONIFY_MIMETYPE': 'application/json; charset=utf-8',
        'MAX_CONTENT_LENGTH': 16 * 1024 * 1024,  # 16MB max file size
        'SEND_FILE_MAX_AGE_DEFAULT': 300,  # 5 minutes cache for static files
    })
    
    # 註冊錯誤處理器
    register_error_handlers(app)
    
    # 註冊 Blueprint (MVC 控制器)
    register_blueprints(app)
    
    return app

def register_error_handlers(app: Flask):
    """註冊錯誤處理器"""
    from views.api_responses import ApiResponseView
    
    @app.errorhandler(404)
    def not_found(error):
        return ApiResponseView.error("API 端點不存在", 404)
    
    @app.errorhandler(405)
    def method_not_allowed(error):
        return ApiResponseView.error("HTTP 方法不被允許", 405)
    
    @app.errorhandler(429)
    def rate_limit_exceeded(error):
        return ApiResponseView.error("請求過於頻繁", 429)
    
    @app.errorhandler(500)
    def internal_error(error):
        logger.error(f"內部伺服器錯誤: {error}")
        return ApiResponseView.error("內部伺服器錯誤", 500)
    
    # 添加 favicon 路由
    @app.route('/favicon.ico')
    def favicon():
        from flask import Response
        # 返回 204 No Content，表示無內容，避免 404 錯誤
        return Response(status=204)
    
    # 添加 CORS 支援
    @app.after_request
    def after_request(response):
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
        return response

def register_blueprints(app: Flask):
    """註冊 Blueprint 控制器"""
    
    # 導入乾淨的控制器
    try:
        from controllers.dashboard_controller import dashboard_bp
        from controllers.api_controller import api_bp
        from controllers.device_controller import device_bp
        from controllers.database_controller import database_bp  # 資料庫 API 控制器
        from controllers.integrated_uart_controller import integrated_uart_bp  # 使用整合版 UART 控制器
        from controllers.integrated_dashboard_controller import integrated_dashboard_bp  # 整合版 Dashboard 控制器
        from controllers.integrated_device_controller import integrated_device_bp  # 整合版 Device 控制器
        from controllers.integrated_home_controller import integrated_home_bp  # 整合版 Home 控制器
        from controllers.realtime_api_controller import realtime_api_bp  # 即時監控 API 控制器
        
        # 註冊 Blueprint
        app.register_blueprint(integrated_home_bp)  # 首頁控制器 (/, /config-summary 等)
        app.register_blueprint(integrated_dashboard_bp)  # 整合版 Dashboard 控制器 (/dashboard) - 先註冊，避免被舊版覆蓋
        # app.register_blueprint(dashboard_bp)  # 暫時註解掉舊版 dashboard_bp，避免路由衝突
        app.register_blueprint(api_bp, url_prefix='/api')
        app.register_blueprint(device_bp)
        app.register_blueprint(database_bp)  # 資料庫 API 控制器 (/api/database/*)
        app.register_blueprint(integrated_uart_bp)  # 整合版 UART 控制器已有完整的 /api/uart 前綴
        app.register_blueprint(integrated_device_bp)  # 整合版 Device 控制器 (/api/device-settings, /db-setting)
        app.register_blueprint(realtime_api_bp)  # 即時監控 API (/api/realtime)
        
        logger.info("所有 Blueprint 已註冊")
    except ImportError as e:
        logger.error(f"導入控制器失敗: {e}")
        raise

def initialize_components():
    """初始化各種組件"""
    
    # 初始化管理器
    config_manager = ConfigManager()
    device_settings_manager = DeviceSettingsManager()
    multi_device_settings_manager = MultiDeviceSettingsManager()
    
    # 初始化離線模式管理器
    offline_mode_manager = create_offline_mode_manager(config_manager)
    
    # 啟動時自動偵測網路狀態
    network_mode = offline_mode_manager.auto_detect_mode()
    logger.info(f"系統啟動模式: {network_mode}")
    
    # 初始化 UART 讀取器（如果可用）
    uart_reader = None
    try:
        from uart_integrated import uart_reader
        logger.info("UART 讀取器初始化成功")
    except ImportError:
        logger.warning("UART 讀取器不可用")
    
    # 初始化資料庫管理器（如果可用）
    database_manager = None
    try:
        if DATABASE_AVAILABLE:
            from database_manager import DatabaseManager
            database_manager = DatabaseManager()
            logger.info("資料庫管理器初始化成功")
    except ImportError:
        logger.warning("資料庫管理器不可用")
    
    # 初始化控制器
    from controllers.dashboard_controller import init_controller as init_dashboard_controller
    from controllers.api_controller import init_controller as init_api_controller
    from controllers.device_controller import init_controller as init_device_controller
    from controllers.realtime_api_controller import init_realtime_api_controller
    
    # 傳遞必要的組件給控制器
    init_dashboard_controller(
        config_manager,
        device_settings_manager,
        database_manager,
        uart_reader
    )
    
    init_api_controller(
        config_manager,
        device_settings_manager
    )
    
    init_device_controller(
        device_settings_manager,
        multi_device_settings_manager
    )
    
    # 初始化即時監控系統
    init_realtime_api_controller()
    
    # 設置 UART 觸發回調（如果 UART 可用）
    if uart_reader:
        _setup_smart_uart_integration(uart_reader, config_manager)
    
    logger.info("所有組件已初始化")
    
    return {
        'config_manager': config_manager,
        'device_settings_manager': device_settings_manager,
        'multi_device_settings_manager': multi_device_settings_manager,
        'offline_mode_manager': offline_mode_manager,
        'database_manager': database_manager,
        'uart_reader': uart_reader
    }


def _setup_smart_uart_integration(uart_reader, config_manager):
    """設置智能 UART 整合"""
    try:
        from services.smart_uart_trigger import get_trigger_manager
        from services.raspi_api_client import RaspberryPiConfig
        
        # 從配置獲取 RAS_pi 設定
        raspi_config = RaspberryPiConfig(
            host=config.RASPBERRY_PI_HOST,
            port=config.RASPBERRY_PI_PORT,
            timeout=config.REQUEST_TIMEOUT,
            poll_interval=config_manager.get('realtime_poll_interval', 10)
        )
        
        # 獲取觸發管理器
        trigger_manager = get_trigger_manager(raspi_config=raspi_config)
        
        # 設置 UART 控制回調
        def uart_start_callback():
            try:
                return uart_reader.start_reading()
            except Exception as e:
                logger.error(f"UART 啟動回調失敗: {e}")
                return False
        
        def uart_stop_callback():
            try:
                return uart_reader.stop_reading()
            except Exception as e:
                logger.error(f"UART 停止回調失敗: {e}")
                return False
        
        def uart_status_callback():
            try:
                return {
                    'is_running': uart_reader.is_running,
                    'data_count': len(getattr(uart_reader, 'data_buffer', [])),
                    'port': getattr(uart_reader, 'port', None),
                    'baudrate': getattr(uart_reader, 'baudrate', None)
                }
            except Exception as e:
                logger.error(f"UART 狀態回調失敗: {e}")
                return {'is_running': False, 'data_count': 0}
        
        trigger_manager.set_uart_callbacks(
            start_callback=uart_start_callback,
            stop_callback=uart_stop_callback,
            status_callback=uart_status_callback
        )
        
        logger.info("智能 UART 整合設置完成")
        
    except Exception as e:
        logger.error(f"設置智能 UART 整合失敗: {e}")


# 建立 Flask 應用程式
app = create_app()

# === 主程式入口 ===
def main():
    """主程式入口"""
    try:
        # Windows 控制台 UTF-8 支援（更安全的方式）
        if os.name == 'nt':
            try:
                os.system('chcp 65001 > nul')  # 設定控制台為 UTF-8
            except:
                pass
        
        # 顯示啟動資訊（使用安全的字符）
        print("=" * 60)
        try:
            print("🚀 H100 Dashboard API 服務啟動中 (MVC 架構)...")
        except UnicodeEncodeError:
            print(">>> H100 Dashboard API 服務啟動中 (MVC 架構)...")
        print("=" * 60)
        
        # 初始化組件
        components = initialize_components()
        
        # 顯示配置資訊
        try:
            print(f"🏠 運行模式: {'獨立模式' if config.STANDALONE_MODE else '本地模式'}")
        except UnicodeEncodeError:
            print(f"運行模式: {'獨立模式' if config.STANDALONE_MODE else '本地模式'}")
            
        try:
            print(f"🌐 監聽地址: {config.HOST}:{config.PORT}")
        except UnicodeEncodeError:
            print(f"監聽地址: {config.HOST}:{config.PORT}")
            
        try:
            print(f"🔧 調試模式: {'啟用' if config.DEBUG else '停用'}")
        except UnicodeEncodeError:
            print(f"調試模式: {'啟用' if config.DEBUG else '停用'}")
        
        if config.STANDALONE_MODE:
            try:
                print(f"🔗 樹莓派地址: {config.RASPBERRY_PI_HOST}:{config.RASPBERRY_PI_PORT}")
            except UnicodeEncodeError:
                print(f"樹莓派地址: {config.RASPBERRY_PI_HOST}:{config.RASPBERRY_PI_PORT}")
        
        # 顯示可用模組狀態
        try:
            print(f"📦 Requests: {'✓' if import_manager.is_available('requests') else '✗'}")
            print(f"📦 psutil: {'✓' if import_manager.is_available('psutil') else '✗'}")
            print(f"📦 資料庫: {'✓' if DATABASE_AVAILABLE else '✗'}")
        except UnicodeEncodeError:
            print(f"Requests: {'YES' if import_manager.is_available('requests') else 'NO'}")
            print(f"psutil: {'YES' if import_manager.is_available('psutil') else 'NO'}")
            print(f"資料庫: {'YES' if DATABASE_AVAILABLE else 'NO'}")
        
        # 顯示 API 端點
        try:
            print("\n🌐 可用的 API 端點:")
        except UnicodeEncodeError:
            print("\n可用的 API 端點:")
        print(f"  - 健康檢查: http://localhost:{config.PORT}/api/health")
        print(f"  - 系統狀態: http://localhost:{config.PORT}/api/status")
        print(f"  - Dashboard: http://localhost:{config.PORT}/dashboard")
        print(f"  - 設備設定: http://localhost:{config.PORT}/db-setting")
        
        print("\n" + "=" * 60)
        try:
            print("🎉 Dashboard API 服務已啟動 (MVC 架構)!")
        except UnicodeEncodeError:
            print("Dashboard API 服務已啟動 (MVC 架構)!")
        print("=" * 60)
        
        # 啟動 Flask 應用程式
        app.run(
            host=config.HOST,
            port=config.PORT,
            debug=config.DEBUG,
            threaded=True
        )
        
    except KeyboardInterrupt:
        logger.info("接收到中斷信號，正在關閉服務...")
        try:
            print("\n👋 Dashboard API 服務已停止")
        except UnicodeEncodeError:
            print("\nDashboard API 服務已停止")
    except Exception as e:
        logger.error(f"啟動服務時發生錯誤: {str(e)}")
        try:
            print(f"❌ 啟動失敗: {str(e)}")
        except UnicodeEncodeError:
            print(f"啟動失敗: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    main()