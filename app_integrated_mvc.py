# app_integrated.py
"""
H100 Dashboard 整合應用程式
使用 MVC 架構和 Flask 工廠模式重構版本
"""

# 修復 charset_normalizer 循環導入問題
import sys

def fix_charset_normalizer():
    """修復 charset_normalizer 循環導入問題的函數"""
    try:
        # 清理可能存在問題的模組
        modules_to_clean = ['charset_normalizer', 'urllib3', 'requests', 'certifi', 'idna']
        for module in modules_to_clean:
            if module in sys.modules:
                del sys.modules[module]
        
        # 嘗試重新導入
        import charset_normalizer
        return True
    except Exception as e:
        print(f"警告: charset_normalizer 修復失敗: {e}")
        return False

# 執行修復
fix_charset_normalizer()

import os
import logging
import platform
from datetime import datetime

# 設定 Python 路徑
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# 導入應用程式工廠
from core.app_factory import create_app

# 導入日誌模型
from models.logging_model import LoggingModel

# 導入其他必要的模組
from config.config_manager import ConfigManager
from device_settings import DeviceSettingsManager
from multi_device_settings import MultiDeviceSettingsManager
from database_manager import DatabaseManager
from uart_integrated import uart_reader

# 安全導入 Dashboard 資料發送模型（可選功能）
try:
    from models.dashboard_data_sender_model import DashboardDataSenderModel
    DASHBOARD_SENDER_AVAILABLE = True
except ImportError as e:
    DASHBOARD_SENDER_AVAILABLE = False
    logging.warning(f"Dashboard 資料發送模型未載入: {e}")
    # 創建一個虛擬的類以防止錯誤
    class DashboardDataSenderModel:
        def __init__(self): 
            self.enabled = False
        def get_sender(self): 
            return self
        def start(self, *args): 
            return False
        @property
        def is_running(self): 
            return False

# 安全導入 FTP 模型
try:
    from models.ftp_model import FTPModel
    FTP_MODEL_AVAILABLE = True
except ImportError as e:
    FTP_MODEL_AVAILABLE = False
    logging.warning(f"FTP 模型未載入: {e}")
    # 創建虛擬 FTP 模型
    class FTPModel:
        def get_local_server(self):
            return self
        @property
        def is_running(self):
            return False

# 檢查是否安裝了 requests
try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    logging.warning("requests 模組未安裝，部分功能將被停用")

# 檢查是否安裝了 flask-monitoringdashboard
try:
    import flask_monitoringdashboard
    DASHBOARD_AVAILABLE = True
except ImportError:
    DASHBOARD_AVAILABLE = False


def create_dashboard_app():
    """創建 Dashboard 應用程式"""
    # 應用程式配置
    config = {
        'DEBUG': True,
        'HOST': '0.0.0.0',
        'PORT': 5000,  # 修改為 5000 端口，適合在樹莓派上作為主服務
        'TEMPLATES_AUTO_RELOAD': True,
        'JSON_AS_ASCII': False,
        'JSON_SORT_KEYS': False,
        'SECRET_KEY': 'integrated_dashboard_secret_key_2025'
    }
    
    # 創建應用程式
    app = create_app(config)
    
    # 設定平台適配的日誌系統
    setup_platform_specific_logging()
    
    # 初始化應用程式組件
    with app.app_context():
        initialize_components(app)
    
    return app


def setup_platform_specific_logging():
    """設定平台特定的日誌系統"""
    # 根據系統類型設定 logs 路徑
    if platform.system() == 'Windows':
        # Windows 系統使用當前目錄下的 logs 資料夾
        log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
    else:
        # Linux/Pi 系統使用樹莓派專用路徑
        log_dir = "/home/pi/my_fastapi_app/logs"
    
    os.makedirs(log_dir, exist_ok=True)  # 自動建立資料夾（如果沒有的話）
    
    # 設定日誌系統
    logging_model = LoggingModel(log_dir=log_dir)
    
    logging.info(f"日誌系統已初始化，日誌目錄: {log_dir}")
    return log_dir


def initialize_components(app):
    """初始化應用程式組件"""
    try:
        # 初始化設定管理器
        config_manager = ConfigManager()
        app.config_manager = config_manager
        
        # 初始化設備設定管理器
        device_settings_manager = DeviceSettingsManager()
        app.device_settings_manager = device_settings_manager
        
        # 初始化多設備設定管理器
        multi_device_settings_manager = MultiDeviceSettingsManager()
        app.multi_device_settings_manager = multi_device_settings_manager
        
        # 初始化資料庫管理器
        database_manager = DatabaseManager()
        app.database_manager = database_manager
        
        # 初始化離線模式管理器
        try:
            from multi_protocol_manager import create_offline_mode_manager
            offline_mode_manager = create_offline_mode_manager(config_manager)
            app.offline_mode_manager = offline_mode_manager
            
            # 啟動時自動偵測網路狀態
            network_mode = offline_mode_manager.auto_detect_mode()
            logging.info(f"系統啟動模式: {network_mode}")
        except Exception as e:
            logging.warning(f"離線模式管理器初始化失敗: {e}")
        
        # 初始化 Dashboard 資料發送器（如果可用）
        if DASHBOARD_SENDER_AVAILABLE:
            dashboard_sender_model = DashboardDataSenderModel()
            app.dashboard_sender_model = dashboard_sender_model
            
            # 如果 UART 正在運行，自動啟動資料發送
            if uart_reader and uart_reader.is_running:
                dashboard_sender = dashboard_sender_model.get_sender()
                if hasattr(dashboard_sender, 'enabled') and dashboard_sender.enabled:
                    dashboard_sender.start(uart_reader)
            
            logging.info("Dashboard 資料發送器已初始化")
        else:
            # 如果無法載入，創建虛擬模型
            app.dashboard_sender_model = DashboardDataSenderModel()
            logging.warning("Dashboard 資料發送器使用虛擬模型")
        
        # 初始化本地 FTP 服務器（如果可用）
        if FTP_MODEL_AVAILABLE:
            ftp_model = FTPModel()
            app.ftp_model = ftp_model
            logging.info("FTP 模型已初始化")
        else:
            app.ftp_model = FTPModel()
            logging.warning("FTP 模型使用虛擬模型")
        
        # 設定 Flask MonitoringDashboard（如果可用）
        if DASHBOARD_AVAILABLE:
            try:
                flask_monitoringdashboard.config.init_from(
                    envvar='FLASK_MONITORING_DASHBOARD_CONFIG',
                    file='dashboard_config.cfg'
                )
                flask_monitoringdashboard.bind(app)
                logging.info("Flask MonitoringDashboard 已成功初始化")
            except Exception as dashboard_error:
                logging.warning(f"Flask MonitoringDashboard 初始化失敗: {dashboard_error}")
        
        # 記錄成功初始化的組件
        components = [
            'ConfigManager',
            'DeviceSettingsManager', 
            'MultiDeviceSettingsManager',
            'DatabaseManager'
        ]
        
        # 添加可選組件
        if DASHBOARD_SENDER_AVAILABLE:
            components.append('DashboardDataSenderModel')
        if FTP_MODEL_AVAILABLE:
            components.append('FTPModel')
        
        logging.info(f"應用程式組件已成功初始化: {', '.join(components)}")
        
    except Exception as e:
        logging.error(f"初始化應用程式組件時發生錯誤: {e}")
        raise


def setup_signal_handlers(app):
    """設定信號處理器"""
    import signal
    
    def signal_handler(sig, frame):
        logging.info('收到中斷信號，正在關閉應用程式...')
        
        # 停止 UART 讀取
        if uart_reader and uart_reader.is_running:
            uart_reader.stop_reading()
            logging.info('UART 讀取已停止')
        
        # 停止 Dashboard 資料發送服務
        if hasattr(app, 'dashboard_sender_model'):
            dashboard_sender = app.dashboard_sender_model.get_sender()
            if dashboard_sender.is_running:
                dashboard_sender.stop()
                logging.info('Dashboard 資料發送服務已停止')
        
        # 停止本地 FTP 服務器
        if hasattr(app, 'ftp_model'):
            local_server = app.ftp_model.get_local_server()
            if local_server.is_running:
                local_server.stop_server()
                logging.info('本地 FTP 服務器已停止')
        
        logging.info('應用程式已安全關閉')
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)


def main():
    """主程式入口"""
    try:
        print("=" * 60)
        print("🚀 H100 Dashboard 整合應用程式 (MVC 架構版 - 樹莓派優化)")
        print("=" * 60)
        print(f"⏰ 啟動時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("📁 工作目錄:", os.getcwd())
        print("🐍 Python 版本:", sys.version.split()[0])
        print(f"🖥️  運行平台: {platform.system()} {platform.release()}")
        
        # 創建應用程式
        app = create_dashboard_app()
        
        # 設定信號處理器
        setup_signal_handlers(app)
        
        # 打印系統資訊
        print("\n📋 系統組件狀態:")
        print(f"   ├─ 配置管理器: ✅ 已載入")
        print(f"   ├─ 設備設定管理: ✅ 已初始化")
        print(f"   ├─ 資料庫管理: ✅ 已連接")
        print(f"   ├─ UART 讀取器: {'✅ 已準備' if uart_reader else '❌ 未就緒'}")
        print(f"   ├─ requests 模組: {'✅ 已安裝' if REQUESTS_AVAILABLE else '❌ 未安裝'}")
        print(f"   └─ MonitoringDashboard: {'✅ 已啟用' if DASHBOARD_AVAILABLE else '❌ 未安裝'}")
        
        print(f"\n🌐 服務啟動資訊:")
        print(f"   ├─ 主機位址: {app.config['HOST']}")
        print(f"   ├─ 連接埠: {app.config['PORT']}")
        print(f"   └─ 偵錯模式: {'啟用' if app.config['DEBUG'] else '停用'}")
        
        print("\n🔗 可用的端點:")
        print("   ├─ 主頁: http://localhost:5000/")
        print("   ├─ 設備設定: http://localhost:5000/db-setting")
        print("   ├─ WiFi 設定: http://localhost:5000/wifi")
        print("   ├─ Dashboard: http://localhost:5000/dashboard")
        if DASHBOARD_AVAILABLE:
            print("   ├─ 監控面板: http://localhost:5000/dashboard/")
        print("   └─ API 文檔: http://localhost:5000/api/")
        
        print("\n" + "=" * 60)
        print("🎯 應用程式已就緒，按 Ctrl+C 停止服務")
        print("=" * 60)
        
        # 啟動應用程式
        app.run(
            host=app.config['HOST'],
            port=app.config['PORT'],
            debug=app.config['DEBUG'],
            threaded=True,
            use_reloader=False  # 避免在重載時出現問題
        )
        
    except Exception as e:
        logging.error(f"應用程式啟動失敗: {e}")
        print(f"❌ 應用程式啟動失敗: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()