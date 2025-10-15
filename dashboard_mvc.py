#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
H100 Dashboard API 服務 - MVC 架構重構版本
與 RAS_pi 系統同步的 API 端點

重構特點：
- 使用 MVC 架構
- 與 RAS_pi 系統 API 完全同步
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

def fix_charset_normalizer():
    """
    修正 charset_normalizer 循環導入問題
    與 RAS_pi 系統保持一致
    """
    try:
        # 步驟1：清除已載入的模組
        modules_to_clean = [
            'charset_normalizer',
            'charset_normalizer.api',
            'charset_normalizer.cd',
            'charset_normalizer.models',
            'charset_normalizer.utils',
            'urllib3',
            'requests',
            'certifi',
            'idna'
        ]

        for module in modules_to_clean:
            if module in sys.modules:
                del sys.modules[module]

        # 步驟2：清除 __pycache__ 快取
        import importlib
        importlib.invalidate_caches()

        # 步驟3：禁用 mypyc 編譯
        os.environ['CHARSET_NORMALIZER_USE_MYPYC'] = '0'

        # 重新導入
        import charset_normalizer
        return True

    except Exception as e:
        print(f"警告: charset_normalizer 修正失敗: {e}")
        return False

# 執行修正
fix_charset_normalizer()

# 在導入其他模組前，先設置環境變數避免 charset_normalizer 問題
os.environ.setdefault('PYTHONIOENCODING', 'utf-8')

# 暫時忽略 charset_normalizer 相關的警告
warnings.filterwarnings('ignore', category=UserWarning, module='charset_normalizer')

import logging
from pathlib import Path
from flask import Flask

# 添加專案根目錄到 Python 路徑
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# === 配置和常數 ===
class DashboardConfig:
    """Dashboard 配置管理 - 與 RAS_pi 系統同步"""
    
    # 基本配置
    SECRET_KEY = 'dashboard_secret_key_2025'
    HOST = '0.0.0.0'
    PORT = 5001
    DEBUG = os.getenv('DEBUG', 'True').lower() == 'true'
    
    # 樹莓派配置 (作為客戶端連接到 RAS_pi 系統)
    RASPBERRY_PI_HOST = os.getenv('RASPBERRY_PI_HOST', '192.168.113.239')
    RASPBERRY_PI_PORT = int(os.getenv('RASPBERRY_PI_PORT', '5000'))
    
    # 模式配置
    STANDALONE_MODE = os.getenv('DASHBOARD_STANDALONE_MODE', 'True').lower() == 'true'
    
    # 與 RAS_pi 同步的性能配置
    API_CACHE_TTL = 60  # API快取TTL (秒)
    DATA_CACHE_TTL = 300  # 數據快取TTL (秒)
    MAX_CACHE_SIZE = 200
    
    # 請求配置
    REQUEST_TIMEOUT = 10
    MAX_RETRIES = 3
    
    # RAS_pi 系統特定配置
    RASPI_API_PREFIX = '/api'
    RASPI_DASHBOARD_PREFIX = '/dashboard'
    RASPI_CONFIG_PREFIX = '/config'

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
    """註冊 Blueprint 控制器 - 與 RAS_pi 系統完全同步"""
    
    # 導入所有控制器 (與 RAS_pi 系統同步)
    try:
        # === 核心控制器 ===
        from controllers.api_controller import api_bp
        from controllers.dashboard_controller import dashboard_bp
        from controllers.device_controller import device_bp
        from controllers.database_controller import database_bp
        from controllers.ftp_controller import ftp_bp
        from controllers.uart_controller import uart_bp
        from controllers.wifi_controller import wifi_bp
        from controllers.network_controller import network_bp
        from controllers.protocol_controller import protocol_bp
        from controllers.mode_controller import mode_bp
        from controllers.multi_protocol_controller import multi_protocol_bp
        
        # === 整合版控制器 (與 RAS_pi 同步) ===
        from controllers.integrated_dashboard_controller import integrated_dashboard_bp
        from controllers.integrated_device_controller import integrated_device_bp
        from controllers.integrated_home_controller import integrated_home_bp
        from controllers.integrated_uart_controller import integrated_uart_bp
        from controllers.integrated_wifi_controller import integrated_wifi_bp
        from controllers.integrated_protocol_controller import integrated_protocol_bp
        
        # === 註冊 Blueprint (按 RAS_pi 系統順序) ===
        
        # 首頁和導航 (最高優先級)
        app.register_blueprint(integrated_home_bp)  # /, /config-summary, /11, /application/<protocol>
        
        # 整合版控制器 (與 RAS_pi 相同)
        app.register_blueprint(integrated_dashboard_bp)  # /dashboard, /api/dashboard/*
        app.register_blueprint(integrated_device_bp)    # /db-setting, /api/device-settings, /api/multi-device-settings
        app.register_blueprint(integrated_uart_bp)      # /api/uart/*
        app.register_blueprint(integrated_wifi_bp)      # /wifi, /api/wifi/*
        app.register_blueprint(integrated_protocol_bp)  # /protocol-config/<protocol>, /api/protocols, /api/protocol-config/<protocol>
        
        # 核心 API 控制器
        app.register_blueprint(api_bp, url_prefix='/api')  # /api/health, /api/status, /api/config, /api/system/*
        
        # 專用控制器
        app.register_blueprint(dashboard_bp)    # 舊版 dashboard 路由
        app.register_blueprint(device_bp)       # 設備管理
        app.register_blueprint(database_bp, url_prefix='/api/database')  # /api/database/*
        app.register_blueprint(ftp_bp, url_prefix='/api/ftp')            # /api/ftp/*
        app.register_blueprint(uart_bp, url_prefix='/api/uart')          # /api/uart/* (舊版)
        app.register_blueprint(wifi_bp, url_prefix='/api/wifi')          # /api/wifi/* (舊版)
        app.register_blueprint(network_bp, url_prefix='/api/network')    # /api/network/*
        app.register_blueprint(protocol_bp, url_prefix='/api/protocol')  # /api/protocol/*
        app.register_blueprint(mode_bp, url_prefix='/api/mode')          # /api/mode/*
        
        # 多協定管理 (如果存在)
        try:
            app.register_blueprint(multi_protocol_bp, url_prefix='/api/multi-protocol')
        except:
            pass  # 多協定控制器可選
        
        logger.info("所有 Blueprint 已註冊 (與 RAS_pi 系統同步)")
        
        # 顯示註冊的路由 (調試用)
        if config.DEBUG:
            logger.info("已註冊的路由:")
            for rule in app.url_map.iter_rules():
                logger.info(f"  {rule.methods} {rule.rule} -> {rule.endpoint}")
                
    except ImportError as e:
        logger.error(f"導入控制器失敗: {e}")
        # 使用基礎控制器作為備用
        try:
            from controllers.api_controller import api_bp
            from controllers.integrated_home_controller import integrated_home_bp
            app.register_blueprint(integrated_home_bp)
            app.register_blueprint(api_bp, url_prefix='/api')
            logger.warning("僅載入基礎控制器")
        except ImportError as fallback_error:
            logger.error(f"載入備用控制器也失敗: {fallback_error}")
            raise

def initialize_components():
    """初始化各種組件 - 與 RAS_pi 系統同步"""
    
    # 初始化配置管理器
    try:
        from config.config_manager import ConfigManager
        config_manager = ConfigManager()
        logger.info("配置管理器初始化成功")
    except ImportError as e:
        logger.error(f"配置管理器初始化失敗: {e}")
        config_manager = None
    
    # 初始化設備管理器
    try:
        from device_settings import DeviceSettingsManager
        from multi_device_settings import MultiDeviceSettingsManager
        device_settings_manager = DeviceSettingsManager()
        multi_device_settings_manager = MultiDeviceSettingsManager()
        logger.info("設備管理器初始化成功")
    except ImportError as e:
        logger.error(f"設備管理器初始化失敗: {e}")
        device_settings_manager = None
        multi_device_settings_manager = None
    
    # 初始化網路工具
    try:
        from network_utils import network_checker, create_offline_mode_manager
        offline_mode_manager = create_offline_mode_manager(config_manager) if config_manager else None
        
        # 啟動時自動偵測網路狀態
        if offline_mode_manager:
            network_mode = offline_mode_manager.auto_detect_mode()
            logger.info(f"系統啟動模式: {network_mode}")
        else:
            logger.warning("離線模式管理器不可用")
            
    except ImportError as e:
        logger.error(f"網路工具初始化失敗: {e}")
        offline_mode_manager = None
    
    # 初始化資料庫管理器（如果可用）
    database_manager = None
    try:
        if DATABASE_AVAILABLE:
            from database_manager import DatabaseManager
            database_manager = DatabaseManager()
            logger.info("資料庫管理器初始化成功")
    except ImportError as e:
        logger.warning(f"資料庫管理器不可用: {e}")
    
    # 初始化 UART 讀取器（如果可用）
    uart_reader = None
    try:
        from uart_integrated import uart_reader
        logger.info("UART 讀取器初始化成功")
    except ImportError as e:
        logger.warning(f"UART 讀取器不可用: {e}")
    
    # 初始化服務層
    uart_service = None
    try:
        from services.uart_service import UARTService
        uart_service = UARTService()
        logger.info("UART 服務初始化成功")
    except ImportError as e:
        logger.warning(f"UART 服務不可用: {e}")
        uart_service = None
    
    # 初始化控制器
    try:
        # 基礎控制器初始化
        from controllers.api_controller import init_controller as init_api_controller
        from controllers.dashboard_controller import init_controller as init_dashboard_controller
        from controllers.device_controller import init_controller as init_device_controller
        
        # 整合版控制器初始化
        from controllers.integrated_dashboard_controller import init_controller as init_integrated_dashboard_controller
        from controllers.integrated_device_controller import init_controller as init_integrated_device_controller
        from controllers.integrated_home_controller import init_controller as init_integrated_home_controller
        from controllers.integrated_uart_controller import init_controller as init_integrated_uart_controller
        
        # 傳遞必要的組件給控制器
        init_api_controller(config_manager, device_settings_manager)
        init_dashboard_controller(config_manager, device_settings_manager, database_manager, uart_reader)
        init_device_controller(device_settings_manager, multi_device_settings_manager)
        
        # 初始化整合版控制器
        init_integrated_dashboard_controller(config_manager, database_manager, uart_reader)
        init_integrated_device_controller(device_settings_manager, multi_device_settings_manager, database_manager)
        init_integrated_home_controller(config_manager, device_settings_manager)
        init_integrated_uart_controller(uart_reader, config_manager)
        
        logger.info("控制器初始化完成")
        
    except ImportError as e:
        logger.warning(f"部分控制器初始化失敗: {e}")
    except AttributeError as e:
        logger.warning(f"控制器初始化函數不存在: {e}")
    
    # 設置 UART 觸發回調（如果 UART 可用）
    if uart_reader:
        _setup_smart_uart_integration(uart_reader, config_manager)
    
    logger.info("所有組件已初始化 (與 RAS_pi 系統同步)")
    
    return {
        'config_manager': config_manager,
        'device_settings_manager': device_settings_manager,
        'multi_device_settings_manager': multi_device_settings_manager,
        'offline_mode_manager': offline_mode_manager,
        'database_manager': database_manager,
        'uart_reader': uart_reader,
        'uart_service': uart_service
    }
    
    init_device_controller(
        device_settings_manager,
        multi_device_settings_manager
    )
    
    # 初始化即時監控系統（如果存在）
    try:
        from controllers.realtime_api_controller import init_realtime_api_controller
        init_realtime_api_controller()
        logger.info("即時監控系統初始化完成")
    except ImportError as e:
        logger.warning(f"即時監控系統不可用: {e}")
    
    # 設置 UART 觸發回調（如果 UART 可用）
    if uart_reader:
        _setup_smart_uart_integration(uart_reader, config_manager)
    
    logger.info("所有組件已初始化 (與 RAS_pi 系統同步)")
    
    return {
        'config_manager': config_manager,
        'device_settings_manager': device_settings_manager,
        'multi_device_settings_manager': multi_device_settings_manager,
        'offline_mode_manager': offline_mode_manager,
        'database_manager': database_manager,
        'uart_reader': uart_reader,
        'uart_service': uart_service
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
    """主程式入口 - 與 RAS_pi 系統同步"""
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
            print("🚀 H100 Dashboard API 服務啟動中 (與 RAS_pi 系統同步)...")
        except UnicodeEncodeError:
            print(">>> H100 Dashboard API 服務啟動中 (與 RAS_pi 系統同步)...")
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
                print(f"🔗 RAS_pi 系統地址: {config.RASPBERRY_PI_HOST}:{config.RASPBERRY_PI_PORT}")
            except UnicodeEncodeError:
                print(f"RAS_pi 系統地址: {config.RASPBERRY_PI_HOST}:{config.RASPBERRY_PI_PORT}")
        
        # 顯示可用模組狀態
        try:
            print(f"📦 Requests: {'✓' if import_manager.is_available('requests') else '✗'}")
            print(f"📦 psutil: {'✓' if import_manager.is_available('psutil') else '✗'}")
            print(f"📦 資料庫: {'✓' if DATABASE_AVAILABLE else '✗'}")
            print(f"📦 UART 服務: {'✓' if components.get('uart_service') else '✗'}")
        except UnicodeEncodeError:
            print(f"Requests: {'YES' if import_manager.is_available('requests') else 'NO'}")
            print(f"psutil: {'YES' if import_manager.is_available('psutil') else 'NO'}")
            print(f"資料庫: {'YES' if DATABASE_AVAILABLE else 'NO'}")
            print(f"UART 服務: {'YES' if components.get('uart_service') else 'NO'}")
        
        # 顯示 API 端點 (與 RAS_pi 同步)
        try:
            print("\n🌐 可用的 API 端點 (與 RAS_pi 系統同步):")
        except UnicodeEncodeError:
            print("\n可用的 API 端點 (與 RAS_pi 系統同步):")
        
        print("  === 核心 API ===")
        print(f"  - 健康檢查: http://localhost:{config.PORT}/api/health")
        print(f"  - 系統狀態: http://localhost:{config.PORT}/api/status")
        print(f"  - 系統配置: http://localhost:{config.PORT}/api/config")
        print(f"  - 離線模式: http://localhost:{config.PORT}/api/system/offline-mode")
        
        print("  === 主要頁面 ===")
        print(f"  - 首頁: http://localhost:{config.PORT}/")
        print(f"  - Dashboard: http://localhost:{config.PORT}/dashboard")
        print(f"  - 配置摘要: http://localhost:{config.PORT}/config-summary")
        print(f"  - 設備設定: http://localhost:{config.PORT}/db-setting")
        
        print("  === 設備管理 API ===")
        print(f"  - 設備設定: http://localhost:{config.PORT}/api/device-settings")
        print(f"  - 多設備管理: http://localhost:{config.PORT}/api/multi-device-settings")
        print(f"  - 資料庫 API: http://localhost:{config.PORT}/api/database/*")
        
        print("  === 通訊管理 API ===")
        print(f"  - UART 管理: http://localhost:{config.PORT}/api/uart/*")
        print(f"  - WiFi 管理: http://localhost:{config.PORT}/api/wifi/*")
        print(f"  - 網路管理: http://localhost:{config.PORT}/api/network/*")
        print(f"  - 協定管理: http://localhost:{config.PORT}/api/protocols")
        
        print("\n" + "=" * 60)
        try:
            print("🎉 H100 Dashboard API 服務已啟動 (與 RAS_pi 系統同步)!")
        except UnicodeEncodeError:
            print("H100 Dashboard API 服務已啟動 (與 RAS_pi 系統同步)!")
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
            print("\n👋 H100 Dashboard API 服務已停止")
        except UnicodeEncodeError:
            print("\nH100 Dashboard API 服務已停止")
    except Exception as e:
        logger.error(f"啟動服務時發生錯誤: {str(e)}")
        try:
            print(f"❌ 啟動失敗: {str(e)}")
        except UnicodeEncodeError:
            print(f"啟動失敗: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    main()