from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, Response, session, make_response, send_from_directory
from config_manager import ConfigManager
from uart_integrated import uart_reader, protocol_manager
from network_utils import network_checker, create_offline_mode_manager
from device_settings import DeviceSettingsManager
from multi_device_settings import MultiDeviceSettingsManager
from database_manager import DatabaseManager
import json
import os
import time
import threading
import subprocess
import sys
import logging
import platform
from datetime import datetime
from logging.handlers import TimedRotatingFileHandler

# 嘗試導入 requests，用於傳送資料到 Dashboard 服務
try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    logging.warning("requests 模組未安裝，將無法傳送資料到 Dashboard 服務")

# 嘗試導入 Flask-MonitoringDashboard，如果沒有安裝則跳過
try:
    import flask_monitoringdashboard as dashboard
    DASHBOARD_AVAILABLE = True
except ImportError:
    DASHBOARD_AVAILABLE = False
    print("Flask-MonitoringDashboard 未安裝，可以執行 'pip install flask-monitoringdashboard' 來安裝")

# 指定 logs 絕對路徑（不要放桌面）
log_dir = "/home/pi/my_fastapi_app/logs"
os.makedirs(log_dir, exist_ok=True)  # 自動建立資料夾（如果沒有的話）

# 建立自訂的日誌處理器，支援按日期自動切換
class DailyLogHandler(TimedRotatingFileHandler):
    def __init__(self, log_dir):
        # 初始日誌檔案名稱
        log_filename = os.path.join(log_dir, f"app_{datetime.now().strftime('%Y%m%d')}.log")
        super().__init__(log_filename, when='midnight', interval=1, backupCount=30, encoding='utf-8')
        self.log_dir = log_dir
        self.suffix = "%Y%m%d"
        
    def rotation_filename(self, default_name):
        # 自訂輪換後的檔案名稱格式
        timestamp = datetime.now().strftime('%Y%m%d')
        return os.path.join(self.log_dir, f"app_{timestamp}.log")

# 設定 logging 使用自動切換日誌處理器
daily_handler = DailyLogHandler(log_dir)
daily_handler.setLevel(logging.INFO)
daily_handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(message)s'))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        daily_handler,
        logging.StreamHandler()
    ]
)

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # 若尚未設置

# CORS 處理
@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization,Cache-Control,Pragma')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    response.headers.add('Access-Control-Max-Age', '3600')  # 預檢請求快取1小時
    return response

# 處理 OPTIONS 預檢請求
@app.before_request
def handle_preflight():
    if request.method == "OPTIONS":
        response = make_response()
        response.headers.add("Access-Control-Allow-Origin", "*")
        response.headers.add('Access-Control-Allow-Headers', "*")
        response.headers.add('Access-Control-Allow-Methods', "*")
        response.headers.add('Access-Control-Max-Age', '3600')
        logging.info(f'處理 OPTIONS 預檢請求: {request.url} from {request.remote_addr}')
        return response

# 設定 Flask Dashboard（如果有安裝的話）
if DASHBOARD_AVAILABLE:
    try:
        # 設定 Dashboard 配置
        app.config['SECRET_KEY'] = 'your_secret_key'
        app.config['DATABASE_URL'] = 'sqlite:///dashboard.db'
        
        # 設定配置檔案路徑
        dashboard_config_path = os.path.join(os.path.dirname(__file__), 'dashboard_config.cfg')
        
        # 檢查配置文件是否存在，如果不存在則創建一個簡單的配置
        if not os.path.exists(dashboard_config_path):
            # 創建一個簡單的英文配置文件，避免編碼問題
            simple_config = """[dashboard]
DATABASE_URL = sqlite:///dashboard.db
SECURITY_TOKEN = your_dashboard_security_token
GUEST_PASSWORD = 
MONITOR_LEVEL = 3
COLLECT_STATIC_DATA = True
COLLECT_ENDPOINT_DATA = True
DATA_RETENTION_DAYS = 30
SHOW_LOGIN_BANNER = False
BRAND_NAME = UART Monitoring System
TITLE_NAME = Flask Dashboard
GRAPH_TYPE = dygraph
ENABLE_LOGGING = True
LOG_LEVEL = INFO
"""
            with open(dashboard_config_path, 'w', encoding='utf-8') as f:
                f.write(simple_config)
        
        # 設定環境變數，指向配置文件
        os.environ['FLASK_MONITORING_DASHBOARD_CONFIG'] = dashboard_config_path
        
        # 初始化 Dashboard，使用 try-catch 避免編碼錯誤
        try:
            dashboard.config.init_from(envvar='FLASK_MONITORING_DASHBOARD_CONFIG')
            dashboard.bind(app)
            print("Flask MonitoringDashboard 已啟用，可以在 /dashboard/ 訪問")
        except (UnicodeDecodeError, UnicodeError) as unicode_error:
            print(f"Dashboard 配置文件編碼錯誤，使用預設配置: {unicode_error}")
            # 使用預設配置
            dashboard.bind(app)
            print("Flask MonitoringDashboard 已啟用（使用預設配置），可以在 /dashboard/ 訪問")
        
        print("Flask Dashboard 已啟用，可以在 /dashboard 訪問")
        
    except Exception as dashboard_error:
        print(f"Flask Dashboard 初始化失敗: {dashboard_error}")
        print("將僅使用基本 Dashboard 功能")
        DASHBOARD_AVAILABLE = False
else:
    print("Flask Dashboard 未啟用（需要安裝 flask-monitoringdashboard 和 psutil）")

# 全域變數暫存模式
current_mode = {'mode': 'idle'}

# 初始化設定管理器
config_manager = ConfigManager()

# 初始化設備設定管理器
device_settings_manager = DeviceSettingsManager()

# 初始化多設備設定管理器
multi_device_settings_manager = MultiDeviceSettingsManager()

# 初始化資料庫管理器
database_manager = DatabaseManager()

# 初始化離線模式管理器
offline_mode_manager = create_offline_mode_manager(config_manager)

# 啟動時自動偵測網路狀態
network_mode = offline_mode_manager.auto_detect_mode()
logging.info(f"系統啟動模式: {network_mode}")

# Dashboard 資料傳送管理器
class DashboardDataSender:
    def __init__(self):
        self.dashboard_url = "http://192.168.113.239:5000"  # 預設 Dashboard 服務地址
        self.api_endpoint = "/api/uart/receive-from-pi"
        self.enabled = REQUESTS_AVAILABLE
        self.send_interval = 10  # 每10秒檢查一次
        self.batch_size = 20  # 批量大小
        self.last_sent_index = 0  # 記錄上次發送的資料索引
        self.is_running = False
        self.send_thread = None
        self.send_queue = []
        self.total_sent = 0
        self.send_errors = 0
        
        # 從設定檔讀取 Dashboard 地址
        self.load_dashboard_config()
        
    def load_dashboard_config(self):
        """從設定檔載入 Dashboard 配置"""
        try:
            # 可以從設定檔或環境變數讀取
            if hasattr(config_manager, 'get_dashboard_config'):
                dashboard_config = config_manager.get_dashboard_config()
                if dashboard_config and 'url' in dashboard_config:
                    self.dashboard_url = dashboard_config['url']
                    logging.info(f"從設定檔讀取 Dashboard 地址: {self.dashboard_url}")
        except Exception as e:
            logging.warning(f"載入 Dashboard 設定失敗，使用預設地址: {e}")
    
    def set_dashboard_url(self, url):
        """設定 Dashboard 服務地址"""
        self.dashboard_url = url
        logging.info(f"Dashboard 服務地址已更新為: {self.dashboard_url}")
    
    def send_single_data(self, data):
        """發送單筆資料到 Dashboard"""
        if not self.enabled:
            return False, "requests 模組未安裝"
            
        try:
            url = f"{self.dashboard_url}{self.api_endpoint}"
            response = requests.post(
                url,
                json=data,
                headers={'Content-Type': 'application/json'},
                timeout=10
            )
            
            if response.status_code == 200:
                self.total_sent += 1
                logging.debug(f"成功發送資料到 Dashboard: MAC={data.get('mac_id')}")
                return True, "發送成功"
            else:
                self.send_errors += 1
                logging.error(f"發送資料失敗: HTTP {response.status_code}")
                return False, f"HTTP錯誤: {response.status_code}"
                
        except requests.exceptions.ConnectionError:
            self.send_errors += 1
            logging.error(f"無法連接到 Dashboard 服務: {self.dashboard_url}")
            return False, "連接失敗"
        except requests.exceptions.Timeout:
            self.send_errors += 1
            logging.error("發送資料超時")
            return False, "發送超時"
        except Exception as e:
            self.send_errors += 1
            logging.error(f"發送資料錯誤: {e}")
            return False, str(e)
    
    def send_batch_data(self, data_list):
        """批量發送資料到 Dashboard"""
        if not self.enabled:
            return False, "requests 模組未安裝"
            
        try:
            batch_data = {'data_list': data_list}
            url = f"{self.dashboard_url}{self.api_endpoint}"
            
            response = requests.post(
                url,
                json=batch_data,
                headers={'Content-Type': 'application/json'},
                timeout=15
            )
            
            if response.status_code == 200:
                self.total_sent += len(data_list)
                logging.info(f"成功批量發送 {len(data_list)} 筆資料到 Dashboard")
                return True, f"批量發送成功: {len(data_list)} 筆"
            else:
                self.send_errors += 1
                logging.error(f"批量發送失敗: HTTP {response.status_code}")
                return False, f"HTTP錯誤: {response.status_code}"
                
        except Exception as e:
            self.send_errors += 1
            logging.error(f"批量發送錯誤: {e}")
            return False, str(e)
    
    def data_sender_worker(self):
        """資料發送工作執行緒"""
        logging.info("🚀 Dashboard 資料發送服務已啟動")
        
        while self.is_running:
            try:
                if not uart_reader or not uart_reader.latest_data:
                    time.sleep(self.send_interval)
                    continue
                
                # 獲取新資料
                with uart_reader.lock:
                    current_data = uart_reader.latest_data.copy()
                
                # 找出需要發送的新資料
                if len(current_data) > self.last_sent_index:
                    new_data = current_data[self.last_sent_index:]
                    
                    if len(new_data) > 0:
                        # 準備發送資料，確保格式正確
                        prepared_data = []
                        for item in new_data:
                            # 確保資料格式符合 Dashboard API 需求
                            if isinstance(item, dict) and all(key in item for key in ['mac_id', 'channel', 'parameter', 'unit']):
                                prepared_data.append(item)
                        
                        if prepared_data:
                            if len(prepared_data) == 1:
                                # 單筆資料
                                success, message = self.send_single_data(prepared_data[0])
                            else:
                                # 批量資料
                                success, message = self.send_batch_data(prepared_data)
                            
                            if success:
                                self.last_sent_index = len(current_data)
                                logging.debug(f"已發送 {len(prepared_data)} 筆資料到 Dashboard")
                            else:
                                logging.warning(f"發送資料失敗: {message}")
                
                time.sleep(self.send_interval)
                
            except Exception as e:
                logging.error(f"資料發送執行緒錯誤: {e}")
                time.sleep(self.send_interval)
        
        logging.info("📤 Dashboard 資料發送服務已停止")
    
    def start(self):
        """啟動資料發送服務"""
        if not self.enabled:
            logging.warning("無法啟動 Dashboard 資料發送服務: requests 模組未安裝")
            return False
            
        if self.is_running:
            logging.warning("Dashboard 資料發送服務已在運行中")
            return False
        
        self.is_running = True
        self.send_thread = threading.Thread(target=self.data_sender_worker, daemon=True)
        self.send_thread.start()
        logging.info(f"✅ Dashboard 資料發送服務已啟動，目標: {self.dashboard_url}")
        return True
    
    def stop(self):
        """停止資料發送服務"""
        if not self.is_running:
            return False
            
        self.is_running = False
        if self.send_thread:
            self.send_thread.join(timeout=5)
        logging.info("🛑 Dashboard 資料發送服務已停止")
        return True
    
    def get_status(self):
        """獲取發送狀態"""
        return {
            'enabled': self.enabled,
            'running': self.is_running,
            'dashboard_url': self.dashboard_url,
            'total_sent': self.total_sent,
            'send_errors': self.send_errors,
            'last_sent_index': self.last_sent_index,
            'send_interval': self.send_interval
        }

# 初始化 Dashboard 資料發送器
dashboard_sender = DashboardDataSender()

# 如果 UART 正在運行，自動啟動資料發送
if uart_reader and uart_reader.is_running:
    dashboard_sender.start()

# 本地FTP測試伺服器管理
class LocalFTPServer:
    def __init__(self):
        self.server_process = None
        self.is_running = False
        self.test_dir = "test_ftp_server"
        self.port = 2121
        self.username = "test_user"
        self.password = "test_password"
        
    def start_server(self):
        """啟動本地FTP測試伺服器"""
        if self.is_running:
            return False, "FTP伺服器已在運行中"
            
        try:
            # 建立測試目錄
            if not os.path.exists(self.test_dir):
                os.makedirs(self.test_dir)
                
            # 檢查pyftpdlib是否安裝
            try:
                import pyftpdlib
            except ImportError:
                return False, "需要安裝 pyftpdlib，請執行: pip install pyftpdlib"
            
            # 啟動FTP伺服器
            from pyftpdlib.authorizers import DummyAuthorizer
            from pyftpdlib.handlers import FTPHandler
            from pyftpdlib.servers import FTPServer
            
            authorizer = DummyAuthorizer()
            authorizer.add_user(self.username, self.password, self.test_dir, perm="elradfmwMT")
            
            handler = FTPHandler
            handler.authorizer = authorizer
            
            server = FTPServer(("127.0.0.1", self.port), handler)
            server.max_cons = 256
            server.max_cons_per_ip = 5
            
            # 在新執行緒中啟動伺服器
            def run_server():
                try:
                    server.serve_forever()
                except Exception as e:
                    print(f"FTP伺服器錯誤: {e}")
                    
            server_thread = threading.Thread(target=run_server, daemon=True)
            server_thread.start()
            
            self.is_running = True
            return True, f"本地FTP測試伺服器已啟動 (127.0.0.1:{self.port})"
            
        except Exception as e:
            return False, f"啟動FTP伺服器失敗: {str(e)}"
            
    def stop_server(self):
        """停止本地FTP測試伺服器"""
        if not self.is_running:
            return False, "FTP伺服器未運行"
            
        try:
            self.is_running = False
            return True, "本地FTP測試伺服器已停止"
        except Exception as e:
            return False, f"停止FTP伺服器失敗: {str(e)}"
            
    def get_status(self):
        """獲取伺服器狀態"""
        return {
            'is_running': self.is_running,
            'host': '127.0.0.1',
            'port': self.port,
            'username': self.username,
            'password': self.password,
            'test_dir': os.path.abspath(self.test_dir)
        }
        
    def update_config_for_test(self):
        """更新config.json為測試設定"""
        try:
            config_file = "config.json"
            if os.path.exists(config_file):
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                
                # 更新FTP設定為本地測試伺服器
                config['protocols']['FTP'] = {
                    "host": "127.0.0.1",
                    "port": self.port,
                    "username": self.username,
                    "password": self.password,
                    "remote_dir": "/",
                    "passive_mode": True
                }
                
                with open(config_file, 'w', encoding='utf-8') as f:
                    json.dump(config, f, indent=2, ensure_ascii=False)
                
                return True, "已更新config.json為測試設定"
            else:
                return False, "config.json檔案不存在"
        except Exception as e:
            return False, f"更新設定失敗: {str(e)}"

# 建立全域FTP伺服器實例
local_ftp_server = LocalFTPServer()

# 主頁面
@app.route('/')
def home():
    logging.info(f'訪問首頁, remote_addr={request.remote_addr}')
    """主頁面"""
    
    # 獲取UART資料
    uart_data = uart_reader.get_latest_data()
    com_port = uart_reader.get_uart_config()[0]
    uart_status = {
        'is_running': uart_reader.is_running,
        'data_count': uart_reader.get_data_count(),
        'latest_data': list(reversed(uart_data[-10:])) if uart_data else [],  # 只顯示最新10筆，最新在最上方
        'com_port': com_port
    }
    
    response = render_template('home.html', 
                         uart_status=uart_status)
    
    # 設定防止快取的 HTTP 標頭
    response = make_response(response)
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    
    return response

@app.route('/test-mac-id')
def test_mac_id():
    """MAC ID 測試頁面"""
    return render_template('mac_id_test.html')

# 設備設定路由
@app.route('/db-setting')
def db_setting():
    """設備設定頁面"""
    logging.info(f'訪問設備設定頁面, remote_addr={request.remote_addr}')
    
    # 檢查是否從 dashboard 重定向過來
    redirect_to_dashboard = request.args.get('redirect', 'false').lower() == 'true'
    
    # 載入當前設備設定
    try:
        current_settings = device_settings_manager.load_settings()
    except Exception as e:
        logging.error(f"載入設備設定時發生錯誤: {e}")
        current_settings = device_settings_manager.default_settings.copy()
    
    return render_template('db_setting.html', 
                         current_settings=current_settings,
                         redirect_to_dashboard=redirect_to_dashboard)

# WiFi 設定路由
@app.route('/wifi')
def wifi_setting():
    """WiFi 設定頁面"""
    logging.info(f'訪問 WiFi 設定頁面, remote_addr={request.remote_addr}')
    return render_template('wifi.html')

@app.route('/api/wifi/scan', methods=['GET','POST'])
def api_wifi_scan():
    """API: 掃描 WiFi 網路"""
    try:
        from wifi_manager import wifi_manager
        networks = wifi_manager.scan_networks()
        
        logging.info(f"掃描到 {len(networks)} 個 WiFi 網路")
        
        return jsonify({
            'success': True,
            'networks': networks
        })
    except Exception as e:
        logging.error(f"WiFi 掃描失敗: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/wifi/connect', methods=['POST'])
def api_wifi_connect():
    """API: 連接到 WiFi 網路"""
    try:
        data = request.get_json()
        ssid = data.get('ssid')
        password = data.get('password', '')
        
        if not ssid:
            return jsonify({
                'success': False,
                'error': 'SSID 不能為空'
            }), 400
        
        from wifi_manager import wifi_manager
        success, message = wifi_manager.connect_to_network(ssid, password)
        
        if success:
            logging.info(f"成功連接到 WiFi: {ssid}")
            return jsonify({
                'success': True,
                'message': message
            })
        else:
            logging.error(f"連接 WiFi 失敗: {message}")
            return jsonify({
                'success': False,
                'error': message
            }), 400
            
    except Exception as e:
        logging.error(f"WiFi 連接 API 錯誤: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/wifi/status')
def api_wifi_status():
    """API: 獲取當前 WiFi 連接狀態"""
    try:
        from wifi_manager import wifi_manager
        status = wifi_manager.get_current_connection()
        
        if status is None:
            return jsonify({
                'connected': False,
                'ssid': None,
                'ip': None,
                'signal': None
            })
        
        return jsonify(status)
        
    except Exception as e:
        logging.error(f"獲取 WiFi 狀態失敗: {e}")
        return jsonify({
            'connected': False,
            'ssid': None,
            'ip': None,
            'signal': None,
            'error': str(e)
        })

@app.route('/api/device-settings', methods=['GET', 'POST'])
def api_device_settings():
    """API: 獲取或儲存設備設定，支援多設備"""
    if request.method == 'GET':
        try:
            # 檢查是否指定了特定的 MAC ID
            mac_id = request.args.get('mac_id')
            
            if mac_id:
                # 獲取特定設備的設定
                settings = multi_device_settings_manager.load_device_settings(mac_id)
                return jsonify({'success': True, 'settings': settings, 'mac_id': mac_id})
            else:
                # 沒有指定 MAC ID，返回傳統的單一設備設定（向後相容）
                settings = device_settings_manager.load_settings()
                return jsonify({'success': True, 'settings': settings})
                
        except Exception as e:
            logging.error(f"獲取設備設定時發生錯誤: {e}")
            return jsonify({'success': False, 'message': f'獲取設定失敗: {str(e)}'})
    
    else:  # POST
        try:
            data = request.get_json()
            if not data:
                return jsonify({'success': False, 'message': '無效的請求資料'})
            
            # 驗證必要欄位
            if not data.get('device_name', '').strip():
                return jsonify({'success': False, 'message': '設備名稱不能為空'})
            
            # 檢查是否有 MAC ID (device_serial)
            mac_id = data.get('device_serial', '').strip()
            
            if mac_id:
                # 有 MAC ID，使用多設備管理器
                if multi_device_settings_manager.save_device_settings(mac_id, data):
                    # 同時將設備資訊保存到資料庫
                    try:
                        # 格式化設備型號
                        device_model = data.get('device_model', {})
                        if isinstance(device_model, dict):
                            # 將多頻道型號合併為字串
                            model_parts = []
                            for channel, model in device_model.items():
                                if model and model.strip():
                                    model_parts.append(f"Ch{channel}:{model}")
                            formatted_model = "; ".join(model_parts) if model_parts else "未設定"
                        else:
                            formatted_model = str(device_model) if device_model else "未設定"
                        
                        device_info = {
                            'mac_id': mac_id,
                            'device_name': data.get('device_name', ''),
                            'device_type': '感測器設備',
                            'device_model': formatted_model,
                            'factory_area': data.get('device_name', ''),  # 使用設備名稱作為廠區
                            'floor_level': '1F',  # 預設樓層，可以後續修改
                            'location_description': data.get('device_location', ''),
                            'installation_date': datetime.now().date().isoformat(),
                            'status': 'active'
                        }
                        database_manager.register_device(device_info)
                        logging.info(f"設備 {mac_id} 資訊已同步到資料庫")
                    except Exception as db_error:
                        logging.warning(f"設備資訊同步到資料庫失敗: {db_error}")
                    
                    response_data = {
                        'success': True, 
                        'message': f'設備 {mac_id} 的設定已成功儲存',
                        'mac_id': mac_id
                    }
                    
                    # 檢查是否需要重定向到 dashboard
                    redirect_to_dashboard = data.get('redirect_to_dashboard', False)
                    if redirect_to_dashboard:
                        response_data['redirect_url'] = url_for('flask_dashboard')
                    
                    return jsonify(response_data)
                else:
                    return jsonify({'success': False, 'message': f'儲存設備 {mac_id} 設定時發生錯誤'})
            else:
                # 沒有 MAC ID，使用傳統的單一設備管理器（向後相容）
                if device_settings_manager.save_settings(data):
                    response_data = {
                        'success': True, 
                        'message': '設備設定已成功儲存'
                    }
                    
                    # 檢查是否需要重定向到 dashboard
                    redirect_to_dashboard = data.get('redirect_to_dashboard', False)
                    if redirect_to_dashboard:
                        response_data['redirect_url'] = url_for('flask_dashboard')
                    
                    return jsonify(response_data)
                else:
                    return jsonify({'success': False, 'message': '儲存設定時發生錯誤'})
                
        except Exception as e:
            logging.error(f"儲存設備設定時發生錯誤: {e}")
            return jsonify({'success': False, 'message': f'處理請求時發生錯誤: {str(e)}'})

@app.route('/api/multi-device-settings')
def api_multi_device_settings():
    """API: 獲取所有設備設定"""
    try:
        all_devices = multi_device_settings_manager.load_all_devices()
        return jsonify({
            'success': True,
            'devices': all_devices,
            'device_count': len(all_devices),
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        logging.error(f"獲取多設備設定時發生錯誤: {e}")
        return jsonify({
            'success': False,
            'message': f'獲取多設備設定失敗: {str(e)}',
            'devices': {}
        })

# Dashboard 相關路由
@app.route('/dashboard')
def flask_dashboard():
    """Flask Dashboard 主頁面"""
    logging.info(f'訪問Flask Dashboard, remote_addr={request.remote_addr}')
    
    # 檢查設備設定是否完成
    if not device_settings_manager.is_configured():
        logging.info("設備尚未設定，重定向到設定頁面")
        flash('請先完成設備設定', 'warning')
        return redirect(url_for('db_setting', redirect='true'))
    
    # 檢查是否有安裝 flask-monitoringdashboard 且已成功初始化
    if DASHBOARD_AVAILABLE:
        try:
            # 嘗試重定向到 Flask MonitoringDashboard
            return redirect('/dashboard/')
        except Exception as redirect_error:
            logging.warning(f"重定向到 MonitoringDashboard 失敗: {redirect_error}")
            # 如果重定向失敗，使用自訂面板
            pass
    
    # 提供基本的系統監控資訊
    try:
        import psutil
        # 在 Windows 系統上，某些 psutil 功能可能需要特殊處理
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
        except:
            cpu_percent = 0
            
        try:
            memory_info = psutil.virtual_memory()._asdict()
        except:
            memory_info = {'percent': 0, 'total': 0, 'available': 0}
            
        try:
            if os.name == 'nt':  # Windows 系統
                disk_info = psutil.disk_usage('C:\\')._asdict()
            else:
                disk_info = psutil.disk_usage('/')._asdict()
        except:
            disk_info = {'percent': 0, 'total': 0, 'free': 0}
            
        try:
            network_info = psutil.net_io_counters()._asdict() if psutil.net_io_counters() else {}
        except:
            network_info = {}
            
        try:
            boot_time = datetime.fromtimestamp(psutil.boot_time()).strftime('%Y-%m-%d %H:%M:%S')
        except:
            boot_time = 'N/A'
            
        system_info = {
            'cpu_percent': cpu_percent,
            'memory': memory_info,
            'disk': disk_info,
            'network': network_info,
            'boot_time': boot_time
        }
    except ImportError:
        system_info = {
            'cpu_percent': 'N/A (需要安裝 psutil)',
            'memory': {'percent': 0},
            'disk': {'percent': 0},
            'network': {},
            'boot_time': 'N/A'
        }
    except Exception as psutil_error:
        logging.error(f"獲取系統資訊時發生錯誤: {psutil_error}")
        system_info = {
            'cpu_percent': 'N/A (系統資訊獲取失敗)',
            'memory': {'percent': 0},
            'disk': {'percent': 0},
            'network': {},
            'boot_time': 'N/A'
        }
    
    # 應用程式統計
    try:
        app_stats = {
            'uart_running': uart_reader.is_running,
            'uart_data_count': uart_reader.get_data_count(),
            'active_protocol': config_manager.get_active_protocol(),
            'offline_mode': config_manager.get('offline_mode', False),
            'supported_protocols': config_manager.get_supported_protocols(),
            'current_mode': current_mode['mode']
        }
    except Exception as app_stats_error:
        logging.error(f"獲取應用程式統計時發生錯誤: {app_stats_error}")
        app_stats = {
            'uart_running': False,
            'uart_data_count': 0,
            'active_protocol': 'N/A',
            'offline_mode': True,
            'supported_protocols': [],
            'current_mode': 'idle'
        }
    
    # 載入設備設定
    try:
        device_settings = device_settings_manager.load_settings()
    except Exception as device_error:
        logging.error(f"載入設備設定時發生錯誤: {device_error}")
        device_settings = {
            'device_name': '未設定設備',
            'device_location': '',
            'device_model': '',
            'device_serial': '',
            'device_description': '',
            'created_at': None,
            'updated_at': None
        }
    
    return render_template('dashboard.html', 
                         system_info=system_info,
                         app_stats=app_stats,
                         device_settings=device_settings)

@app.route('/api/dashboard/stats')
def dashboard_stats():
    """API: 獲取 Dashboard 統計資料"""
    try:
        # 系統資源資訊
        try:
            import psutil
            # Windows 系統特殊處理
            try:
                cpu_percent = psutil.cpu_percent(interval=0.1)
            except:
                cpu_percent = 0
                
            try:
                memory_percent = psutil.virtual_memory().percent
            except:
                memory_percent = 0
                
            try:
                if os.name == 'nt':  # Windows 系統
                    disk_percent = psutil.disk_usage('C:\\').percent
                else:
                    disk_percent = psutil.disk_usage('/').percent
            except:
                disk_percent = 0
                
            try:
                net_io = psutil.net_io_counters()
                network_sent = net_io.bytes_sent if net_io else 0
                network_recv = net_io.bytes_recv if net_io else 0
            except:
                network_sent = 0
                network_recv = 0
                
            system_stats = {
                'cpu_percent': cpu_percent,
                'memory_percent': memory_percent,
                'disk_percent': disk_percent,
                'network_sent': network_sent,
                'network_recv': network_recv,
            }
        except ImportError:
            system_stats = {
                'cpu_percent': 0,
                'memory_percent': 0,
                'disk_percent': 0,
                'network_sent': 0,
                'network_recv': 0,
            }
        except Exception as psutil_error:
            logging.error(f"獲取系統統計時發生錯誤: {psutil_error}")
            system_stats = {
                'cpu_percent': 0,
                'memory_percent': 0,
                'disk_percent': 0,
                'network_sent': 0,
                'network_recv': 0,
            }
        
        # 應用程式統計
        try:
            app_stats = {
                'uart_running': uart_reader.is_running,
                'uart_data_count': uart_reader.get_data_count(),
                'active_protocol': config_manager.get_active_protocol(),
                'offline_mode': config_manager.get('offline_mode', False),
                'current_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'ftp_server_running': local_ftp_server.is_running
            }
        except Exception as app_error:
            logging.error(f"獲取應用程式統計時發生錯誤: {app_error}")
            app_stats = {
                'uart_running': False,
                'uart_data_count': 0,
                'active_protocol': 'N/A',
                'offline_mode': True,
                'current_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'ftp_server_running': False
            }
        
        # 載入設備設定
        try:
            device_settings = device_settings_manager.load_settings()
        except Exception as device_error:
            logging.error(f"載入設備設定時發生錯誤: {device_error}")
            device_settings = {
                'device_name': '未設定設備',
                'device_location': '',
                'device_model': '',
                'device_serial': '',
                'device_description': ''
            }
        
        return jsonify({
            'success': True,
            'system': system_stats,
            'application': app_stats,
            'device_settings': device_settings,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logging.error(f"獲取 Dashboard 統計資料時發生錯誤: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'獲取統計資料失敗: {str(e)}',
            'system': {
                'cpu_percent': 0,
                'memory_percent': 0,
                'disk_percent': 0,
                'network_sent': 0,
                'network_recv': 0,
            },
            'application': {
                'uart_running': False,
                'uart_data_count': 0,
                'active_protocol': 'N/A',
                'offline_mode': True,
                'current_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'ftp_server_running': False
            },
            'device_settings': {
                'device_name': '未設定設備',
                'device_location': '',
                'device_model': '',
                'device_serial': '',
                'device_description': ''
            }
        })

@app.route('/api/dashboard/device-settings')
def dashboard_device_settings():
    """API: 獲取設備設定資料"""
    try:
        device_settings = device_settings_manager.load_settings()
        return jsonify({
            'success': True,
            'device_settings': device_settings,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        logging.error(f"獲取設備設定時發生錯誤: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'獲取設備設定失敗: {str(e)}',
            'device_settings': {
                'device_name': '未設定設備',
                'device_location': '',
                'device_model': '',
                'device_serial': '',
                'device_description': ''
            }
        })

@app.route('/api/dashboard/chart-data')
def dashboard_chart_data():
    """API: 獲取圖表數據 - 按通道分組的時間序列數據，支援特定MAC ID過濾"""
    try:
        # 獲取查詢參數
        limit = request.args.get('limit', 10000, type=int)  # 預設最近100000筆數據，如需更多可調整參數
        channel = request.args.get('channel', None, type=int)  # 特定通道，None表示所有通道
        mac_id = request.args.get('mac_id', None)  # 特定MAC ID，None表示所有設備
        
        # 記錄 API 請求 - 降低頻繁請求的日誌級別
        if limit <= 1000:  # 小量請求用DEBUG級別
            logging.debug(f"圖表數據請求 - limit={limit}, channel={channel}, mac_id={mac_id}, IP={request.remote_addr}")
        else:  # 大量請求用INFO級別
            logging.info(f"圖表數據請求 - limit={limit}, channel={channel}, mac_id={mac_id}, IP={request.remote_addr}")
        
        # 從 uart_reader 獲取數據
        if not uart_reader or not hasattr(uart_reader, 'latest_data'):
            logging.warning("UART數據源不可用")
            return jsonify({
                'success': False,
                'message': 'UART數據源不可用',
                'data': {}
            })
        
        # 獲取原始數據
        with uart_reader.lock:
            raw_data = uart_reader.latest_data.copy()
        
        # 記錄數據狀態
        total_data_count = len(raw_data)
        logging.info(f"原始數據總數: {total_data_count}")
        
        # 如果沒有數據，直接返回
        if total_data_count == 0:
            logging.info("沒有可用的UART數據")
            return jsonify({
                'success': True,
                'data': [],
                'total_channels': 0,
                'filtered_by_mac_id': mac_id,
                'timestamp': datetime.now().isoformat()
            })
        
        # 按通道分組數據
        chart_data = {}
        
        # 計算30分鐘前的時間點
        from datetime import datetime, timedelta
        thirty_minutes_ago = datetime.now() - timedelta(minutes=30)
        
        # 過濾和處理數據
        filtered_count = 0
        for entry in raw_data[-limit:]:  # 取最近的數據
            entry_channel = entry.get('channel', 0)
            entry_mac_id = entry.get('mac_id', 'N/A')
            entry_timestamp_str = entry.get('timestamp')
            
            # 解析時間戳並檢查是否在30分鐘內
            try:
                if entry_timestamp_str:
                    # 嘗試多種時間格式解析
                    entry_timestamp = None
                    for fmt in ['%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M:%S.%f', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%dT%H:%M:%S.%f']:
                        try:
                            entry_timestamp = datetime.strptime(entry_timestamp_str, fmt)
                            break
                        except ValueError:
                            continue
                    
                    # 如果無法解析時間戳，嘗試作為ISO格式
                    if entry_timestamp is None:
                        try:
                            entry_timestamp = datetime.fromisoformat(entry_timestamp_str.replace('Z', '+00:00'))
                        except:
                            entry_timestamp = datetime.now()  # 使用當前時間作為備份
                    
                    # 檢查數據是否在30分鐘時間窗口內
                    if entry_timestamp < thirty_minutes_ago:
                        filtered_count += 1
                        continue  # 跳過超過30分鐘的舊數據
                else:
                    # 如果沒有時間戳，使用當前時間
                    entry_timestamp = datetime.now()
            except Exception as e:
                logging.warning(f"解析時間戳失敗: {entry_timestamp_str}, 錯誤: {e}")
                entry_timestamp = datetime.now()  # 使用當前時間作為備份
            
            # 如果指定了特定通道，只返回該通道的數據
            if channel is not None and entry_channel != channel:
                continue
            
            # 如果指定了特定MAC ID，只返回該設備的數據
            if mac_id is not None and entry_mac_id != mac_id:
                continue
            
            # 確保通道存在於結果中
            if entry_channel not in chart_data:
                chart_data[entry_channel] = {
                    'channel': entry_channel,
                    'unit': entry.get('unit', 'N/A'),
                    'mac_id': entry_mac_id,
                    'data': []
                }
            
            # 新增數據點
            chart_data[entry_channel]['data'].append({
                'timestamp': entry.get('timestamp'),
                'parameter': entry.get('parameter', 0),
                'mac_id': entry_mac_id
            })
        
        # 轉換為列表格式並按通道排序
        result_data = list(chart_data.values())
        result_data.sort(key=lambda x: x['channel'])
        
        # 記錄處理結果
        processed_data_count = sum(len(channel_data['data']) for channel_data in result_data)
        logging.info(f"圖表數據處理完成 - 通道數: {len(result_data)}, 數據點總數: {processed_data_count}, 過濾掉30分鐘外數據: {filtered_count}筆, 處理時間: {datetime.now().isoformat()}")
        
        return jsonify({
            'success': True,
            'data': result_data,
            'total_channels': len(result_data),
            'filtered_by_mac_id': mac_id,
            'time_window_minutes': 30,
            'filtered_old_data_count': filtered_count,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logging.error(f"獲取圖表數據時發生錯誤: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'獲取圖表數據失敗: {str(e)}',
            'data': {}
        })

@app.route('/api/dashboard/devices')
def dashboard_devices():
    """API: 獲取所有設備列表 - 根據MAC ID分組顯示設備資訊"""
    try:
        # 從 uart_reader 獲取數據
        if not uart_reader or not hasattr(uart_reader, 'latest_data'):
            return jsonify({
                'success': False,
                'message': 'UART數據源不可用',
                'devices': []
            })
        
        # 獲取原始數據
        with uart_reader.lock:
            raw_data = uart_reader.latest_data.copy()
        
        # 按MAC ID分組設備
        devices_info = {}
        
        for entry in raw_data:
            mac_id = entry.get('mac_id', 'N/A')
            
            if mac_id == 'N/A' or not mac_id:
                continue
            
            if mac_id not in devices_info:
                devices_info[mac_id] = {
                    'mac_id': mac_id,
                    'device_name': '',
                    'device_location': '',
                    'device_model': '',
                    'device_description': '',
                    'data_count': 0,
                    'last_data_time': None,
                    'is_active': False,
                    'channels': set()
                }
            
            # 更新設備資訊
            device = devices_info[mac_id]
            device['data_count'] += 1
            device['channels'].add(entry.get('channel', 0))
            
            # 更新最後數據時間
            entry_time = entry.get('timestamp')
            if entry_time:
                if not device['last_data_time'] or entry_time > device['last_data_time']:
                    device['last_data_time'] = entry_time
        
        # 檢查設備是否活躍（最近30秒內有數據）
        current_time = datetime.now()
        for device in devices_info.values():
            if device['last_data_time']:
                try:
                    last_time = datetime.fromisoformat(device['last_data_time'].replace('Z', '+00:00'))
                    if hasattr(last_time, 'replace'):
                        last_time = last_time.replace(tzinfo=None)
                    time_diff = (current_time - last_time).total_seconds()
                    device['is_active'] = time_diff <= 30  # 30秒內視為活躍
                except:
                    device['is_active'] = False
            
            # 轉換 channels set 為 list
            device['channels'] = sorted(list(device['channels']))
        
        # 嘗試從多設備設定檔載入設備詳細資訊
        try:
            all_device_settings = multi_device_settings_manager.load_all_devices()
            # 更新每個設備的詳細資訊
            for mac_id, device in devices_info.items():
                if mac_id in all_device_settings:
                    device_config = all_device_settings[mac_id]
                    device['device_name'] = device_config.get('device_name', '')
                    device['device_location'] = device_config.get('device_location', '')
                    device['device_model'] = device_config.get('device_model', '')
                    device['device_description'] = device_config.get('device_description', '')
                else:
                    # 如果在多設備設定中沒有找到，檢查是否在傳統設定中（向後相容）
                    device_settings = device_settings_manager.load_settings()
                    if device_settings.get('device_serial') == mac_id:
                        device['device_name'] = device_settings.get('device_name', '')
                        device['device_location'] = device_settings.get('device_location', '')
                        device['device_model'] = device_settings.get('device_model', '')
                        device['device_description'] = device_settings.get('device_description', '')
        except Exception as settings_error:
            logging.warning(f"載入設備設定時發生錯誤: {settings_error}")
            # 如果多設備設定載入失敗，嘗試載入傳統設定（向後相容）
            try:
                device_settings = device_settings_manager.load_settings()
                # 如果設備設定中有設備序號(MAC ID)，更新對應設備的詳細資訊
                for mac_id, device in devices_info.items():
                    if device_settings.get('device_serial') == mac_id:
                        device['device_name'] = device_settings.get('device_name', '')
                        device['device_location'] = device_settings.get('device_location', '')
                        device['device_model'] = device_settings.get('device_model', '')
                        device['device_description'] = device_settings.get('device_description', '')
            except Exception as fallback_error:
                logging.warning(f"載入傳統設備設定時發生錯誤: {fallback_error}")
        
        # 轉換為列表並按MAC ID排序
        devices_list = list(devices_info.values())
        devices_list.sort(key=lambda x: x['mac_id'])
        
        return jsonify({
            'success': True,
            'devices': devices_list,
            'total_devices': len(devices_list),
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logging.error(f"獲取設備列表時發生錯誤: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'獲取設備列表失敗: {str(e)}',
            'devices': []
        })

@app.route('/api/dashboard/overview')
def dashboard_overview_api():
    """API: 儀表板總覽頁面專用 - 提供綜合統計資訊"""
    try:
        # 獲取系統統計
        stats_response = dashboard_stats()
        stats_data = stats_response.get_json() if hasattr(stats_response, 'get_json') else {}
        
        # 獲取設備資訊
        devices_response = dashboard_devices()
        devices_data = devices_response.get_json() if hasattr(devices_response, 'get_json') else {}
        
        # 獲取 MAC ID 列表
        mac_response = get_uart_mac_ids()
        mac_data = mac_response.get_json() if hasattr(mac_response, 'get_json') else {}
        
        # 計算總覽統計
        total_devices = devices_data.get('total_devices', 0) if devices_data.get('success') else 0
        online_devices = 0
        total_data_count = 0
        
        if devices_data.get('success') and devices_data.get('devices'):
            for device in devices_data['devices']:
                if device.get('is_active', False):
                    online_devices += 1
                total_data_count += device.get('data_count', 0)
        
        # 系統資訊
        system_info = {}
        if stats_data.get('success') and stats_data.get('system'):
            system_info = stats_data['system']
        
        # 構建回應
        overview_data = {
            'success': True,
            'system': {
                'total_devices': total_devices,
                'online_devices': online_devices,
                'total_data_count': total_data_count,
                'cpu_percent': system_info.get('cpu_percent', 0),
                'memory_percent': system_info.get('memory', {}).get('percent', 0),
                'disk_percent': system_info.get('disk', {}).get('percent', 0),
                'network_active': bool(system_info.get('network', {})),
                'boot_time': system_info.get('boot_time'),
                'mac_count': len(mac_data.get('mac_ids', [])) if mac_data.get('success') else 0
            },
            'statistics': {
                'devices_configured': total_devices,
                'active_connections': online_devices,
                'today_data_count': total_data_count,  # 可以進一步過濾今日數據
                'avg_data_rate': '10筆/分',  # 模擬數據，實際可計算
                'data_accuracy': '99.5%',   # 模擬數據
                'protocol_count': 3,        # UART, TCP, UDP
                'config_status': 'normal',
                'last_backup': 'yesterday'  # 模擬數據
            },
            'timestamp': datetime.now().isoformat()
        }
        
        return jsonify(overview_data)
    
    except Exception as e:
        logging.exception(f'獲取總覽統計時發生錯誤: {str(e)}')
        return jsonify({
            'success': False,
            'message': f'獲取總覽統計失敗: {str(e)}',
            'system': {},
            'statistics': {}
        })

# 協定設定頁面
@app.route('/protocol-config/<protocol>')
def protocol_config(protocol):
    logging.info(f'訪問協定設定頁面: {protocol}, remote_addr={request.remote_addr}')
    """特定協定的設定頁面"""
    if not config_manager.validate_protocol(protocol):
        flash('不支援的協定', 'error')
        return redirect(url_for('home'))
    
    # 獲取當前設定
    current_config = config_manager.get_protocol_config(protocol)
    field_info = config_manager.get_protocol_field_info(protocol)
    description = config_manager.get_protocol_description(protocol)
    
    return render_template('protocol_config.html',
                         protocol=protocol,
                         current_config=current_config,
                         field_info=field_info,
                         description=description)

# 儲存協定設定
@app.route('/save-protocol-config/<protocol>', methods=['POST'])
def save_protocol_config(protocol):
    logging.info(f'儲存協定設定: {protocol}, 表單資料: {request.form.to_dict()}, remote_addr={request.remote_addr}')
    print('收到儲存請求:', protocol)
    print('表單資料:', request.form.to_dict())
    
    if not config_manager.validate_protocol(protocol):
        return jsonify({'success': False, 'message': '不支援的協定'})
    
    try:
        # 檢查是否為離線模式
        offline_mode = config_manager.get('offline_mode', False)
        
        # 獲取表單資料
        form_data = request.form.to_dict()
        
        # 處理數值型欄位
        field_info = config_manager.get_protocol_field_info(protocol)
        processed_config = {}
        
        for field, value in form_data.items():
            if field in field_info:
                field_config = field_info[field]
                
                # 根據欄位類型處理值
                if field_config['type'] == 'number':
                    if value:
                        try:
                            # 先嘗試轉換為浮點數，如果是整數則轉為int
                            float_val = float(value)
                            if float_val.is_integer():
                                processed_config[field] = int(float_val)
                            else:
                                processed_config[field] = float_val
                        except ValueError:
                            processed_config[field] = field_config.get('default', 0)
                    else:
                        processed_config[field] = field_config.get('default', 0)
                elif field_config['type'] == 'checkbox':
                    processed_config[field] = field in form_data
                else:
                    processed_config[field] = value
        
        # 在離線模式下跳過網路相關的驗證
        if not offline_mode:
            # 驗證設定
            errors = config_manager.validate_protocol_config(protocol, processed_config)
            if errors:
                return jsonify({
                    'success': False, 
                    'message': '設定驗證失敗',
                    'errors': errors
                })
        
        # 儲存設定
        if config_manager.update_protocol_config(protocol, processed_config):
            config_manager.load_config()
            
            # 自動將此協定設為啟用協定
            if config_manager.set_active_protocol(protocol):
                logging.info(f"成功設定啟用協定為: {protocol}")
                # 驗證設定是否真的生效
                current_active = config_manager.get_active_protocol()
                logging.info(f"驗證: 目前啟用協定為: {current_active}")
            else:
                logging.error(f"設定啟用協定失敗: {protocol}")
            
            # 自動啟動已設定的協定（不僅限於MQTT）
            try:
                from uart_integrated import protocol_manager
                protocol_manager.start(protocol)
                logging.info(f"自動啟動協定: {protocol}")
            except Exception as e:
                logging.warning(f"自動啟動協定 {protocol} 失敗: {e}")
            
            message = f'{protocol} 設定已成功儲存並啟動'
            if offline_mode:
                message += '（離線模式）'
            
            flash(message, 'success')
            return jsonify({
                'success': True, 
                'message': '設定已儲存',
                'redirect_to_home': True,
                'redirect_delay': 1000  # 1秒後重定向
            })
        else:
            return jsonify({'success': False, 'message': '儲存設定時發生錯誤'})
            
    except Exception as e:
        logging.exception(f'儲存協定設定失敗: {str(e)}')
        return jsonify({'success': False, 'message': f'處理設定時發生錯誤: {str(e)}'})

# 設定摘要頁面
@app.route('/config-summary')
def config_summary():
    """設定摘要頁面"""
    all_configs = {}
    for protocol in config_manager.get_supported_protocols():
        all_configs[protocol] = {
            'config': config_manager.get_protocol_config(protocol),
            'description': config_manager.get_protocol_description(protocol)
        }
    
    return render_template('config_summary.html', configs=all_configs)

# 儀表板總覽頁面
@app.route('/11')
def dashboard_11():
    """儀表板總覽頁面 (11.html)"""
    logging.info(f'訪問儀表板總覽頁面 11.html, remote_addr={request.remote_addr}')
    return render_template('11.html')

# 應用介面
@app.route('/application/<protocol>')
def application_interface(protocol):
    """特定協定的應用介面"""
    if not config_manager.validate_protocol(protocol):
        flash('不支援的協定', 'error')
        return redirect(url_for('home'))
    # 啟動對應協定的接收器
    protocol_manager.start(protocol)
    # 獲取協定設定
    config = config_manager.get_protocol_config(protocol)
    description = config_manager.get_protocol_description(protocol)
    return render_template('application.html',
                         protocol=protocol,
                         config=config,
                         description=description)

# API 路由
@app.route('/api/protocols')
def get_protocols():
    """API: 獲取支援的協定列表"""
    protocols = config_manager.get_supported_protocols()
    result = []
    
    for protocol in protocols:
        result.append({
            'name': protocol,
            'description': config_manager.get_protocol_description(protocol)
        })
    
    return jsonify(result)

@app.route('/api/protocol-config/<protocol>')
def get_protocol_config_api(protocol):
    """API: 獲取協定設定"""
    if not config_manager.validate_protocol(protocol):
        return jsonify({'success': False, 'message': '不支援的協定'})
    
    config = config_manager.get_protocol_config(protocol)
    field_info = config_manager.get_protocol_field_info(protocol)
    
    return jsonify({
        'success': True,
        'config': config,
        'field_info': field_info,
        'description': config_manager.get_protocol_description(protocol)
    })

@app.route('/api/config')
def get_all_config():
    """API: 獲取所有設定"""
    return jsonify(config_manager.get_all())

# UART 相關 API
@app.route('/api/uart/test', methods=['POST'])
def test_uart_connection():
    """API: 測試UART連接"""
    try:
        success, message = uart_reader.test_uart_connection()
        return jsonify({'success': success, 'message': message})
    except Exception as e:
        return jsonify({'success': False, 'message': f'測試UART連接時發生錯誤: {str(e)}'})

@app.route('/api/uart/ports')
def list_uart_ports():
    """API: 列出可用的串口"""
    try:
        ports = uart_reader.list_available_ports()
        return jsonify({'success': True, 'ports': ports})
    except Exception as e:
        return jsonify({'success': False, 'message': f'列出串口時發生錯誤: {str(e)}'})

@app.route('/api/uart/start', methods=['POST'])
def start_uart():
    logging.info(f'API: 開始UART讀取, remote_addr={request.remote_addr}')
    try:
        if uart_reader.is_running:
            return jsonify({'success': True, 'message': 'UART已在運行'})
        
        # 先測試UART連接
        test_success, test_message = uart_reader.test_uart_connection()
        if not test_success:
            # 列出可用串口
            available_ports = uart_reader.list_available_ports()
            port_info = ', '.join([f"{p['device']}({p['description']})" for p in available_ports]) if available_ports else "無可用串口"
            
            return jsonify({
                'success': False, 
                'message': f'UART連接測試失敗: {test_message}',
                'available_ports': available_ports,
                'suggestion': f'可用串口: {port_info}'
            })
        
        # 檢查網路狀態並自動設定離線模式
        try:
            network_status = network_checker.get_network_status()
            if not network_status['internet_available']:
                if not config_manager.get('offline_mode', False):
                    logging.info("偵測到無網路連接，自動啟用離線模式")
                    offline_mode_manager.enable_offline_mode()
        except Exception as network_error:
            logging.warning(f"網路檢查失敗，繼續以離線模式運行: {network_error}")
            offline_mode_manager.enable_offline_mode()
        
        # 檢查是否為離線模式
        offline_mode = config_manager.get('offline_mode', False)
        if offline_mode:
            logging.info("離線模式：UART讀取將在離線模式下啟動")
        
        if uart_reader.start_reading():
            message = 'UART讀取已開始'
            if offline_mode:
                message += '（離線模式）'
            else:
                # 在線模式下啟動資料發送到 Dashboard
                if dashboard_sender.enabled and not dashboard_sender.is_running:
                    if dashboard_sender.start():
                        message += '，資料發送服務已啟動'
                    else:
                        message += '，但資料發送服務啟動失敗'
            
            return jsonify({'success': True, 'message': message})
        else:
            # 提供更詳細的錯誤診斷
            available_ports = uart_reader.list_available_ports()
            com_port, _, _, _, _, _ = uart_reader.get_uart_config()
            
            error_details = {
                'success': False,
                'message': 'UART讀取啟動失敗',
                'details': {
                    'configured_port': com_port,
                    'available_ports': available_ports,
                    'suggestions': [
                        f'檢查設備是否連接: ls -la {com_port}',
                        '檢查用戶權限: sudo usermod -a -G dialout $USER',
                        '重新載入驅動: sudo modprobe ftdi_sio',
                        '檢查USB設備: lsusb',
                        '查看系統日誌: dmesg | tail'
                    ]
                }
            }
            
            return jsonify(error_details)
    except Exception as e:
        logging.exception(f'啟動UART時發生錯誤: {str(e)}')
        return jsonify({'success': False, 'message': f'啟動UART時發生錯誤: {str(e)}'})

@app.route('/api/uart/stop', methods=['POST'])
def stop_uart():
    logging.info(f'API: 停止UART讀取, remote_addr={request.remote_addr}')
    try:
        uart_reader.stop_reading()
        
        # 同時停止資料發送服務
        message = 'UART讀取已停止'
        if dashboard_sender.is_running:
            if dashboard_sender.stop():
                message += '，資料發送服務已停止'
            else:
                message += '，但資料發送服務停止失敗'
        
        return jsonify({'success': True, 'message': message})
    except Exception as e:
        logging.exception(f'停止UART時發生錯誤: {str(e)}')
        return jsonify({'success': False, 'message': f'停止UART時發生錯誤: {str(e)}'})

@app.route('/api/uart/status')
def uart_status():
    """API: 獲取UART狀態"""
    try:
        data = uart_reader.get_latest_data()
        return jsonify({
            'success': True,
            'is_running': uart_reader.is_running,
            'data_count': uart_reader.get_data_count(),
            'latest_data': data[-20:] if data else []  # 返回最新20筆資料
        })
    except Exception as e:
        return jsonify({'success': False, 'message': f'獲取UART狀態時發生錯誤: {str(e)}'})

@app.route('/api/uart/clear', methods=['POST'])
def clear_uart_data():
    """API: 清除UART資料"""
    try:
        uart_reader.clear_data()
        return jsonify({'success': True, 'message': 'UART資料已清除'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'清除UART資料時發生錯誤: {str(e)}'})

@app.route('/api/uart/mac-ids', methods=['GET'])
def get_uart_mac_ids():
    """API: 獲取UART接收到的MAC ID列表"""
    try:
        logging.info(f'API請求: /api/uart/mac-ids from {request.remote_addr}')
        
        data = uart_reader.get_latest_data()
        logging.info(f'UART數據總數: {len(data) if data else 0}')
        data_source = 'UART即時數據'
        
        # 修正：如果即時數據為空或MAC ID數量少於預期，強制載入歷史數據
        if not data or len(set(entry.get('mac_id') for entry in data if entry.get('mac_id') and entry.get('mac_id') not in ['N/A', '', None])) < 1:
            logging.info('即時數據不足，嘗試從歷史文件載入MAC ID')
            uart_reader.load_historical_data(days_back=7)  # 載入最近7天的數據
            data = uart_reader.get_latest_data()
            data_source = '歷史文件增強載入'
            logging.info(f'從歷史文件增強載入數據: {len(data) if data else 0} 筆')
            
        if not data:
            logging.warning('沒有可用的UART數據')
            return jsonify({
                'success': True, 
                'mac_ids': [], 
                'data_source': data_source,
                'message': '暫無UART數據，請先啟動UART讀取或檢查歷史數據'
            })
        
        # 從UART數據中提取所有的MAC ID
        mac_ids = []
        valid_mac_count = 0
        
        for entry in data:
            mac_id = entry.get('mac_id')
            if mac_id and mac_id not in ['N/A', '', None]:
                valid_mac_count += 1
                mac_ids.append(mac_id)
        
        # 去重複並排序
        unique_mac_ids = sorted(list(set(mac_ids)))
        
        logging.info(f'MAC ID 處理結果: 總數據{len(data)}, 有效MAC數據{valid_mac_count}, 唯一MAC ID數{len(unique_mac_ids)}')
        if unique_mac_ids:
            logging.info(f'找到的 MAC IDs: {unique_mac_ids}')

        return jsonify({
            'success': True,
            'mac_ids': unique_mac_ids,
            'data_source': data_source,
            'total_records': len(data),
            'unique_mac_count': len(unique_mac_ids),
            'valid_mac_records': valid_mac_count,
            'message': f'找到 {len(unique_mac_ids)} 個唯一的 MAC ID (來源: {data_source})'
        })
        
    except Exception as e:
        logging.exception(f'獲取MAC ID列表時發生錯誤: {str(e)}')
        return jsonify({
            'success': False, 
            'message': f'獲取MAC ID列表時發生錯誤: {str(e)}',
            'mac_ids': []
        })

@app.route('/api/uart/mac-channels/<mac_id>', methods=['GET'])
def get_mac_channels(mac_id):
    """API: 獲取特定MAC ID的頻道資訊"""
    try:
        data = uart_reader.get_latest_data()
        
        if not data:
            return jsonify({
                'success': False,
                'channels': [],
                'message': '暫無UART數據，請先啟動UART讀取'
            })
        
        # 過濾指定MAC ID的數據
        mac_data = [entry for entry in data if entry.get('mac_id') == mac_id]
        
        if not mac_data:
            return jsonify({
                'success': False,
                'channels': [],
                'message': f'找不到MAC ID {mac_id} 的數據'
            })
        
        # 從數據中提取頻道資訊
        channels = set()
        for entry in mac_data:
            channel = entry.get('channel')
            unit = entry.get('unit', '')
            
            # 只包含頻道0-6（電流測量），排除頻道7（電壓測量）
            if channel is not None and str(channel).isdigit():
                channel_num = int(channel)
                if 0 <= channel_num <= 6 and unit == 'A':  # 只包含電流頻道
                    channels.add(channel_num)
        
        # 轉換為排序的列表
        sorted_channels = sorted(list(channels))
        
        return jsonify({
            'success': True,
            'channels': sorted_channels,
            'mac_id': mac_id,
            'total_data_points': len(mac_data),
            'message': f'MAC ID {mac_id} 有 {len(sorted_channels)} 個可配置頻道'
        })
        
    except Exception as e:
        logging.exception(f'獲取MAC ID {mac_id} 的頻道資訊時發生錯誤: {str(e)}')
        return jsonify({
            'success': False,
            'channels': [],
            'message': f'獲取頻道資訊時發生錯誤: {str(e)}'
        })

@app.route('/api/uart/mac-data/<mac_id>', methods=['GET'])
def get_mac_data_10min(mac_id):
    """API: 獲取特定MAC ID最近10分鐘的電流數據"""
    try:
        # 獲取時間範圍參數，預設為10分鐘
        minutes = request.args.get('minutes', 10, type=int)
        
        # 獲取原始數據
        data = uart_reader.get_latest_data()
        
        if not data:
            return jsonify({
                'success': False,
                'data': [],
                'message': '暫無UART數據，請先啟動UART讀取'
            })
        
        # 計算時間範圍
        from datetime import datetime, timedelta
        time_limit = datetime.now() - timedelta(minutes=minutes)
        
        # 過濾指定MAC ID和時間範圍內的數據
        filtered_data = []
        for entry in data:
            if entry.get('mac_id') != mac_id:
                continue
                
            # 只包含電流數據 (單位為 'A')
            if entry.get('unit') != 'A':
                continue
                
            # 檢查時間戳
            entry_timestamp_str = entry.get('timestamp')
            if entry_timestamp_str:
                try:
                    # 嘗試多種時間格式解析
                    entry_timestamp = None
                    for fmt in ['%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M:%S.%f', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%dT%H:%M:%S.%f']:
                        try:
                            entry_timestamp = datetime.strptime(entry_timestamp_str, fmt)
                            break
                        except ValueError:
                            continue
                    
                    # 如果無法解析時間戳，嘗試作為ISO格式
                    if entry_timestamp is None:
                        try:
                            entry_timestamp = datetime.fromisoformat(entry_timestamp_str.replace('Z', '+00:00'))
                        except:
                            continue  # 跳過無法解析的數據
                    
                    # 檢查數據是否在指定時間範圍內
                    if entry_timestamp < time_limit:
                        continue  # 跳過超過時間範圍的舊數據
                        
                except Exception as e:
                    logging.warning(f"解析時間戳失敗: {entry_timestamp_str}, 錯誤: {e}")
                    continue  # 跳過解析失敗的數據
            else:
                # 如果沒有時間戳，假設是最新數據
                pass
            
            # 添加到結果中
            filtered_data.append({
                'timestamp': entry.get('timestamp'),
                'current': float(entry.get('parameter', 0)),
                'channel': entry.get('channel', 0),
                'mac_id': entry.get('mac_id'),
                'unit': entry.get('unit', 'A')
            })
        
        # 按時間戳排序
        filtered_data.sort(key=lambda x: x['timestamp'] or '')
        
        logging.info(f'獲取MAC ID {mac_id} 最近 {minutes} 分鐘數據: {len(filtered_data)} 筆')
        
        return jsonify({
            'success': True,
            'data': filtered_data,
            'mac_id': mac_id,
            'time_range_minutes': minutes,
            'total_data_points': len(filtered_data),
            'message': f'MAC ID {mac_id} 最近 {minutes} 分鐘有 {len(filtered_data)} 筆電流數據'
        })
        
    except Exception as e:
        logging.exception(f'獲取MAC ID {mac_id} 數據時發生錯誤: {str(e)}')
        return jsonify({
            'success': False,
            'data': [],
            'message': f'獲取數據時發生錯誤: {str(e)}'
        })

@app.route('/api/uart/diagnostic', methods=['POST'])
def uart_diagnostic():
    """API: 執行UART診斷"""
    try:
        import subprocess
        import sys
        import os
        
        # 執行診斷腳本
        diagnostic_script = os.path.join(os.path.dirname(__file__), 'uart_diagnostic.py')
        
        if os.path.exists(diagnostic_script):
            result = subprocess.run([sys.executable, diagnostic_script], 
                                  capture_output=True, text=True, timeout=30)
            
            diagnostic_output = result.stdout
            if result.stderr:
                diagnostic_output += f"\n錯誤輸出:\n{result.stderr}"
                
            return jsonify({
                'success': True,
                'diagnostic_output': diagnostic_output,
                'return_code': result.returncode
            })
        else:
            # 如果診斷腳本不存在，執行基本診斷
            com_port, baud_rate, _, _, _, _ = uart_reader.get_uart_config()
            available_ports = uart_reader.list_available_ports()
            
            diagnostic_info = f"""UART基本診斷報告
{'='*40}

配置信息:
  端口: {com_port}
  波特率: {baud_rate}

設備檢查:
  配置的設備是否存在: {'是' if os.path.exists(com_port) else '否'}

可用串口:"""
            
            if available_ports:
                for port in available_ports:
                    diagnostic_info += f"\n  {port['device']} - {port['description']}"
            else:
                diagnostic_info += "\n  沒有找到可用串口"
                
            diagnostic_info += f"""

建議檢查:
  1. 檢查硬體連接
  2. 檢查設備權限: sudo chmod 666 {com_port}
  3. 加入用戶群組: sudo usermod -a -G dialout $USER
  4. 重新載入驅動: sudo modprobe ftdi_sio
  5. 檢查USB設備: lsusb
  6. 查看系統日誌: dmesg | tail
"""
            
            return jsonify({
                'success': True,
                'diagnostic_output': diagnostic_info
            })
            
    except subprocess.TimeoutExpired:
        return jsonify({'success': False, 'message': '診斷超時'})
    except Exception as e:
        logging.exception(f'UART診斷失敗: {str(e)}')
        return jsonify({'success': False, 'message': f'診斷執行失敗: {str(e)}'})



@app.route('/api/uart/stream')
def uart_stream():
    """API: Server-Sent Events 串流UART資料，推送所有新資料"""
    def generate():
        # 只推送新進來的資料
        last_index = len(uart_reader.get_latest_data())
        while True:
            try:
                data = uart_reader.get_latest_data()
                if data and last_index < len(data):
                    new_data = data[last_index:]
                    for d in new_data:
                        yield f"data: {json.dumps(d, ensure_ascii=False)}\n\n"
                    last_index = len(data)
                time.sleep(0.5)
            except Exception as e:
                yield f"data: {json.dumps({'error': str(e)}, ensure_ascii=False)}\n\n"
                time.sleep(2)
    return Response(generate(), mimetype='text/event-stream')

# 匯出設定
@app.route('/export-config')
def export_config():
    """匯出設定"""
    try:
        export_data = {
            'general_config': config_manager.get_all(),
            'protocol_configs': {}
        }
        
        for protocol in config_manager.get_supported_protocols():
            export_data['protocol_configs'][protocol] = config_manager.get_protocol_config(protocol)
        
        return jsonify(export_data)
    except Exception as e:
        return jsonify({'success': False, 'message': f'匯出設定時發生錯誤: {str(e)}'})

# 匯入設定
@app.route('/import-config', methods=['POST'])
def import_config():
    """匯入設定"""
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'message': '沒有選擇檔案'})
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'success': False, 'message': '沒有選擇檔案'})
        
        if file and file.filename and file.filename.endswith('.json'):
            # 讀取檔案內容
            content = file.read().decode('utf-8')
            import_data = json.loads(content)
            
            # 匯入設定
            if config_manager.import_config_from_dict(import_data):
                return jsonify({'success': True, 'message': '設定匯入成功'})
            else:
                return jsonify({'success': False, 'message': '設定匯入失敗'})
        else:
            return jsonify({'success': False, 'message': '不支援的檔案格式'})
            
    except Exception as e:
        return jsonify({'success': False, 'message': f'匯入設定時發生錯誤: {str(e)}'})


@app.route('/api/active-protocol', methods=['GET', 'POST'])
def api_active_protocol():
    """取得或設定目前啟用的通訊協定"""
    if request.method == 'GET':
        protocol = config_manager.get_active_protocol()
        return jsonify({'success': True, 'active_protocol': protocol})
    else:
        data = request.get_json()
        protocol = data.get('protocol')
        if config_manager.set_active_protocol(protocol):
            return jsonify({'success': True, 'active_protocol': protocol})
        else:
            return jsonify({'success': False, 'message': '無效的協定名稱'})

@app.route('/api/protocol/status', methods=['GET'])
def api_protocol_status():
    """API: 獲取協定運行狀態"""
    try:
        from uart_integrated import protocol_manager
        
        # 獲取目前啟用的協定
        active_protocol = config_manager.get_active_protocol()
        
        # 檢查協定管理器中的活動協定
        running_protocol = getattr(protocol_manager, 'active', None)
        
        return jsonify({
            'success': True,
            'active_protocol': active_protocol,
            'running_protocol': running_protocol,
            'is_running': running_protocol is not None and running_protocol == active_protocol
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'獲取協定狀態失敗: {str(e)}'
        })

@app.route('/api/protocol/configured-status', methods=['GET'])
def api_protocol_configured_status():
    """API: 獲取所有協定的設定狀態"""
    try:
        protocol_status = {}
        for protocol in config_manager.get_supported_protocols():
            # 使用配置管理器的 is_protocol_configured 方法檢查設定狀態
            is_configured = config_manager.is_protocol_configured(protocol)
            
            protocol_status[protocol] = {
                'configured': is_configured,
                'description': config_manager.get_protocol_description(protocol)
            }
        
        return jsonify({
            'success': True,
            'protocol_status': protocol_status
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'獲取協定設定狀態失敗: {str(e)}'
        })

@app.route('/api/protocol/start', methods=['POST'])
def api_start_protocol():
    """API: 啟動指定的通訊協定"""
    try:
        data = request.get_json() or {}
        protocol = data.get('protocol')
        
        if not protocol:
            # 如果沒有指定協定，嘗試啟動目前設定的啟用協定
            protocol = config_manager.get_active_protocol()
            
        if not protocol or protocol == 'None':
            return jsonify({
                'success': False,
                'message': '沒有指定要啟動的協定，請先設定通訊協定'
            })
        
        # 檢查協定是否已設定
        if not config_manager.is_protocol_configured(protocol):
            return jsonify({
                'success': False,
                'message': f'{protocol} 協定尚未設定，請先完成設定'
            })
        
        # 檢查離線模式
        offline_mode = config_manager.get('offline_mode', False)
        
        # 啟動協定
        try:
            from uart_integrated import protocol_manager
            protocol_manager.start(protocol)
            
            # 設定為啟用協定
            config_manager.set_active_protocol(protocol)
            
            message = f'{protocol} 通訊協定已成功啟動'
            if offline_mode:
                message += '（離線模式）'
            
            return jsonify({
                'success': True,
                'message': message,
                'active_protocol': protocol
            })
            
        except Exception as e:
            logging.exception(f'啟動 {protocol} 協定失敗: {str(e)}')
            return jsonify({
                'success': False,
                'message': f'啟動 {protocol} 協定失敗: {str(e)}'
            })
            
    except Exception as e:
        logging.exception(f'處理協定啟動請求失敗: {str(e)}')
        return jsonify({
            'success': False,
            'message': f'處理請求失敗: {str(e)}'
        })

@app.route('/api/ftp/upload', methods=['POST'])
def ftp_manual_upload():
    logging.info(f'API: 手動觸發FTP上傳, remote_addr={request.remote_addr}')
    try:
        if protocol_manager.active == 'FTP':
            ftp_receiver = protocol_manager.protocols['FTP']
            # 觸發立即上傳
            ftp_receiver._upload_data()
            return jsonify({'success': True, 'message': 'FTP上傳已觸發'})
        else:
            return jsonify({'success': False, 'message': 'FTP協定未啟用'})
    except Exception as e:
        logging.exception(f'FTP上傳失敗: {str(e)}')
        return jsonify({'success': False, 'message': f'FTP上傳失敗: {str(e)}'})

@app.route('/api/ftp/status')
def ftp_status():
    """API: 獲取FTP狀態"""
    try:
        if protocol_manager.active == 'FTP':
            ftp_receiver = protocol_manager.protocols['FTP']
            return jsonify({
                'success': True,
                'is_running': ftp_receiver.is_running,
                'data_count': len(ftp_receiver.get_latest_data()),
                'last_upload_time': ftp_receiver.last_upload_time,
                'upload_interval': ftp_receiver.upload_interval
            })
        else:
            return jsonify({'success': False, 'message': 'FTP協定未啟用'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'獲取FTP狀態失敗: {str(e)}'})

# 本地FTP測試伺服器 API
@app.route('/api/ftp/local/start', methods=['POST'])
def local_ftp_start():
    """API: 啟動本地FTP測試伺服器"""
    success, message = local_ftp_server.start_server()
    return jsonify({'success': success, 'message': message})

@app.route('/api/ftp/local/stop', methods=['POST'])
def local_ftp_stop():
    """API: 停止本地FTP測試伺服器"""
    success, message = local_ftp_server.stop_server()
    return jsonify({'success': success, 'message': message})

@app.route('/api/ftp/local/status')
def local_ftp_status():
    """API: 獲取本地FTP測試伺服器狀態"""
    status = local_ftp_server.get_status()
    return jsonify(status)

@app.route('/api/ftp/local/update-config', methods=['POST'])
def local_ftp_update_config():
    """API: 更新config.json為本地FTP測試伺服器設定"""
    success, message = local_ftp_server.update_config_for_test()
    return jsonify({'success': success, 'message': message})

@app.route('/api/ftp/test-connection', methods=['POST'])
def ftp_test_connection():
    logging.info(f'API: 測試FTP連接, remote_addr={request.remote_addr}, data={request.get_json(silent=True)}')
    try:
        import ftplib
        import socket
        
        config = config_manager.get_protocol_config('FTP')
        host = config.get('host', 'localhost')
        port = config.get('port', 21)
        username = config.get('username', '')
        password = config.get('password', '')
        passive_mode = config.get('passive_mode', True)
        
        # 測試TCP連接
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10)
        result = sock.connect_ex((host, port))
        sock.close()
        
        if result != 0:
            return jsonify({'success': False, 'message': f'無法連接到 {host}:{port}'})
        
        # 測試FTP連接
        ftp = ftplib.FTP()
        ftp.connect(host, port, timeout=30)
        
        if passive_mode:
            ftp.set_pasv(True)
            
        ftp.login(username, password)
        
        # 測試目錄存取
        remote_dir = config.get('remote_dir', '/')
        ftp.cwd(remote_dir)
        files = ftp.nlst()
        
        ftp.quit()
        
        return jsonify({
            'success': True, 
            'message': f'FTP連接成功，目錄中有 {len(files)} 個檔案'
        })
        
    except ftplib.error_perm as e:
        return jsonify({'success': False, 'message': f'認證失敗: {str(e)}'})
    except Exception as e:
        logging.exception(f'FTP連接失敗: {str(e)}')
        return jsonify({'success': False, 'message': f'連接失敗: {str(e)}'})

@app.route('/api/ftp/test-upload', methods=['POST'])
def ftp_test_upload():
    logging.info(f'API: 測試FTP檔案上傳, remote_addr={request.remote_addr}, data={request.get_json(silent=True)}')
    try:
        import ftplib
        from datetime import datetime
        import json
        
        config = config_manager.get_protocol_config('FTP')
        host = config.get('host', 'localhost')
        port = config.get('port', 21)
        username = config.get('username', '')
        password = config.get('password', '')
        passive_mode = config.get('passive_mode', True)
        remote_dir = config.get('remote_dir', '/')
        
        # 連接FTP
        ftp = ftplib.FTP()
        ftp.connect(host, port, timeout=30)
        
        if passive_mode:
            ftp.set_pasv(True)
            
        ftp.login(username, password)
        ftp.cwd(remote_dir)
        
        # 生成測試檔案
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"test_upload_{timestamp}.json"
        
        test_data = {
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'test_type': 'web_interface_test',
            'message': '這是透過Web介面測試上傳的檔案'
        }
        
        # 上傳檔案
        from io import BytesIO
        data_stream = BytesIO(json.dumps(test_data, ensure_ascii=False, indent=2).encode('utf-8'))
        ftp.storbinary(f'STOR {filename}', data_stream)
        
        # 驗證檔案
        files = ftp.nlst()
        if filename in files:
            file_size = ftp.size(filename)
            ftp.quit()
            return jsonify({
                'success': True, 
                'message': f'測試檔案上傳成功: {filename} ({file_size} bytes)'
            })
        else:
            ftp.quit()
            return jsonify({'success': False, 'message': '檔案上傳後未找到'})
            
    except ftplib.error_perm as e:
        return jsonify({'success': False, 'message': f'上傳權限不足: {str(e)}'})
    except Exception as e:
        logging.exception(f'FTP檔案上傳失敗: {str(e)}')
        return jsonify({'success': False, 'message': f'上傳失敗: {str(e)}'})

# ========== 資料庫相關 API 端點 ==========

@app.route('/api/database/factory-areas', methods=['GET'])
def api_get_factory_areas():
    """API: 獲取所有廠區列表"""
    try:
        factory_areas = database_manager.get_factory_areas()
        return jsonify({
            'success': True,
            'data': factory_areas,
            'count': len(factory_areas)
        })
    except Exception as e:
        logging.error(f"獲取廠區列表失敗: {e}")
        return jsonify({
            'success': False,
            'message': f'獲取廠區列表失敗: {str(e)}',
            'data': []
        })

@app.route('/api/database/floor-levels', methods=['GET'])
def api_get_floor_levels():
    """API: 獲取樓層列表"""
    try:
        factory_area = request.args.get('factory_area')
        floor_levels = database_manager.get_floor_levels(factory_area)
        return jsonify({
            'success': True,
            'data': floor_levels,
            'count': len(floor_levels),
            'factory_area': factory_area
        })
    except Exception as e:
        logging.error(f"獲取樓層列表失敗: {e}")
        return jsonify({
            'success': False,
            'message': f'獲取樓層列表失敗: {str(e)}',
            'data': []
        })

@app.route('/api/database/mac-ids', methods=['GET'])
def api_get_mac_ids():
    """API: 獲取 MAC ID 列表"""
    try:
        factory_area = request.args.get('factory_area')
        floor_level = request.args.get('floor_level')
        mac_ids = database_manager.get_mac_ids(factory_area, floor_level)
        return jsonify({
            'success': True,
            'data': mac_ids,
            'count': len(mac_ids),
            'factory_area': factory_area,
            'floor_level': floor_level
        })
    except Exception as e:
        logging.error(f"獲取 MAC ID 列表失敗: {e}")
        return jsonify({
            'success': False,
            'message': f'獲取 MAC ID 列表失敗: {str(e)}',
            'data': []
        })

@app.route('/api/database/device-models', methods=['GET'])
def api_get_device_models():
    """API: 獲取設備型號列表"""
    try:
        factory_area = request.args.get('factory_area')
        floor_level = request.args.get('floor_level')
        mac_id = request.args.get('mac_id')
        device_models = database_manager.get_device_models(factory_area, floor_level, mac_id)
        return jsonify({
            'success': True,
            'data': device_models,
            'count': len(device_models),
            'factory_area': factory_area,
            'floor_level': floor_level,
            'mac_id': mac_id
        })
    except Exception as e:
        logging.error(f"獲取設備型號列表失敗: {e}")
        return jsonify({
            'success': False,
            'message': f'獲取設備型號列表失敗: {str(e)}',
            'data': []
        })

@app.route('/api/database/chart-data', methods=['GET'])
def api_get_chart_data():
    """API: 獲取圖表數據"""
    try:
        # 獲取篩選參數
        factory_area = request.args.get('factory_area')
        floor_level = request.args.get('floor_level')
        mac_id = request.args.get('mac_id')
        device_model = request.args.get('device_model')
        data_type = request.args.get('data_type', 'current')
        limit = int(request.args.get('limit', 100))
        
        # 構建篩選條件
        filters = {}
        if factory_area:
            filters['factory_area'] = factory_area
        if floor_level:
            filters['floor_level'] = floor_level
        if mac_id:
            filters['mac_id'] = mac_id
        if device_model:
            filters['device_model'] = device_model
            
        chart_data = database_manager.get_chart_data(data_type, filters, limit)
        return jsonify({
            'success': True,
            'data': chart_data,
            'count': len(chart_data),
            'data_type': data_type,
            'filters': filters
        })
    except Exception as e:
        logging.error(f"獲取圖表數據失敗: {e}")
        return jsonify({
            'success': False,
            'message': f'獲取圖表數據失敗: {str(e)}',
            'data': []
        })

@app.route('/api/database/statistics', methods=['GET'])
def api_get_statistics():
    """API: 獲取統計數據"""
    try:
        # 獲取篩選參數
        factory_area = request.args.get('factory_area')
        floor_level = request.args.get('floor_level')
        mac_id = request.args.get('mac_id')
        device_model = request.args.get('device_model')
        
        # 構建篩選條件
        filters = {}
        if factory_area:
            filters['factory_area'] = factory_area
        if floor_level:
            filters['floor_level'] = floor_level
        if mac_id:
            filters['mac_id'] = mac_id
        if device_model:
            filters['device_model'] = device_model
            
        statistics = database_manager.get_statistics(filters)
        return jsonify({
            'success': True,
            'data': statistics,
            'filters': filters
        })
    except Exception as e:
        logging.error(f"獲取統計數據失敗: {e}")
        return jsonify({
            'success': False,
            'message': f'獲取統計數據失敗: {str(e)}',
            'data': {}
        })

@app.route('/api/database/latest-data', methods=['GET'])
def api_get_latest_data():
    """API: 獲取最新數據"""
    try:
        # 獲取篩選參數
        factory_area = request.args.get('factory_area')
        floor_level = request.args.get('floor_level')
        mac_id = request.args.get('mac_id')
        device_model = request.args.get('device_model')
        limit = int(request.args.get('limit', 10))
        
        # 構建篩選條件
        filters = {}
        if factory_area:
            filters['factory_area'] = factory_area
        if floor_level:
            filters['floor_level'] = floor_level
        if mac_id:
            filters['mac_id'] = mac_id
        if device_model:
            filters['device_model'] = device_model
            
        latest_data = database_manager.get_latest_data(filters, limit)
        return jsonify({
            'success': True,
            'data': latest_data,
            'count': len(latest_data),
            'filters': filters
        })
    except Exception as e:
        logging.error(f"獲取最新數據失敗: {e}")
        return jsonify({
            'success': False,
            'message': f'獲取最新數據失敗: {str(e)}',
            'data': []
        })

@app.route('/api/database/test-current-data', methods=['POST'])
def api_add_test_current_data():
    """API: 添加測試電流數據"""
    try:
        import random
        from datetime import datetime, timedelta
        
        # 生成測試數據
        test_data_list = []
        for i in range(10):  # 生成10筆測試數據
            timestamp = datetime.now() - timedelta(minutes=i*5)
            test_data = {
                'timestamp': timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                'mac_id': 'TEST_MAC_001',
                'device_type': '測試設備',
                'device_model': '測試型號H100',
                'factory_area': '測試廠區A',
                'floor_level': '1F',
                'current': round(random.uniform(5.0, 15.0), 2),
                'voltage': round(random.uniform(220.0, 240.0), 2),
                'temperature': round(random.uniform(20.0, 35.0), 1),
                'status': 'active'
            }
            test_data_list.append(test_data)
            
            # 保存到資料庫
            database_manager.save_uart_data(test_data)
        
        return jsonify({
            'success': True,
            'message': f'成功添加 {len(test_data_list)} 筆測試電流數據',
            'data_count': len(test_data_list)
        })
    except Exception as e:
        logging.error(f"添加測試數據失敗: {e}")
        return jsonify({
            'success': False,
            'message': f'添加測試數據失敗: {str(e)}'
        })

# ========== 結束資料庫相關 API 端點 ==========

# 錯誤處理
@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('500.html'), 500

@app.route('/get-mode', methods=['GET'])
def get_mode():
    return jsonify({'mode': current_mode['mode']})

@app.route('/set-mode', methods=['POST'])
def set_mode():
    data = request.get_json()
    mode = data.get('mode')
    if mode in ['idle', 'work']:
        old_mode = current_mode['mode']
        current_mode['mode'] = mode
        
        # 如果切換到工作模式，自動啟動已設定的協定
        activated_protocol = None
        if mode == 'work' and old_mode != 'work':
            try:
                # 獲取已設定的協定
                configured_protocols = []
                for protocol in config_manager.get_supported_protocols():
                    if config_manager.is_protocol_configured(protocol):
                        configured_protocols.append(protocol)
                
                # 如果有已設定的協定，啟動第一個
                if configured_protocols:
                    active_protocol = configured_protocols[0]
                    config_manager.set_active_protocol(active_protocol)
                    activated_protocol = active_protocol
                    
                    # 嘗試啟動協定
                    try:
                        from uart_integrated import protocol_manager
                        protocol_manager.start(active_protocol)
                        logging.info(f"工作模式啟動協定: {active_protocol}")
                    except Exception as e:
                        logging.warning(f"啟動協定 {active_protocol} 失敗: {e}")
                        
            except Exception as e:
                logging.error(f"工作模式自動啟動協定失敗: {e}")
        
        # 取得目前啟用的協定
        current_active = config_manager.get_active_protocol()
        
        return jsonify({
            'mode': mode, 
            'success': True,
            'active_protocol': current_active,
            'activated_protocol': activated_protocol  # 本次切換啟動的協定
        })
    return jsonify({'success': False, 'msg': '無效模式'}), 400

@app.route('/api/system/status')
def system_status():
    """API: 獲取系統狀態，包括網路和離線模式"""
    try:
        # 使用網路檢查器獲取狀態
        network_status = network_checker.get_network_status()
        offline_mode = config_manager.get('offline_mode', False)
        
        # 獲取當前WiFi連接資訊
        current_wifi = None
        try:
            current_wifi = network_checker.get_current_wifi_info()
            logging.info(f"當前WiFi資訊: {current_wifi}")
        except Exception as wifi_error:
            logging.warning(f"獲取WiFi資訊失敗: {wifi_error}")
        
        return jsonify({
            'success': True,
            'network_status': network_status,
            'current_wifi': current_wifi,
            'offline_mode': offline_mode,
            'current_mode': current_mode['mode'],
            'system_info': {
                'platform': sys.platform,
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
        })
    except Exception as e:
        return jsonify({
            'success': False, 
            'message': f'獲取系統狀態失敗: {str(e)}',
            'offline_mode': True,
            'current_wifi': None,
            'network_status': {
                'internet_available': False,
                'local_network_available': False,
                'default_gateway': None,
                'platform': sys.platform
            }
        })

@app.route('/api/system/offline-mode', methods=['POST'])
def toggle_offline_mode():
    """API: 切換離線模式"""
    try:
        data = request.get_json() or {}
        offline_mode = data.get('offline_mode')
        
        if offline_mode is None:
            # 如果沒有指定，則切換模式
            offline_mode = not config_manager.get('offline_mode', False)
        
        if offline_mode:
            offline_mode_manager.enable_offline_mode()
        else:
            offline_mode_manager.disable_offline_mode()
        
        return jsonify({
            'success': True,
            'offline_mode': offline_mode,
            'message': f'已{"啟用" if offline_mode else "停用"}離線模式'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'切換離線模式失敗: {str(e)}'
        })

@app.route('/api/wifi/scan')
def scan_wifi():
    """API: 掃描可用的WiFi網路"""
    try:
        logging.info("開始WiFi掃描請求...")
        wifi_networks = network_checker.scan_wifi_networks()
        
        logging.info(f"WiFi掃描完成，找到 {len(wifi_networks)} 個網路")
        for network in wifi_networks:
            logging.info(f"網路: {network}")
            
        return jsonify({
            'success': True,
            'networks': wifi_networks,
            'count': len(wifi_networks),
            'platform': sys.platform,
            'debug_info': {
                'system': platform.system(),
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
        })
    except Exception as e:
        logging.error(f"WiFi掃描API錯誤: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'WiFi掃描失敗: {str(e)}',
            'networks': [],
            'debug_info': {
                'error': str(e),
                'system': platform.system(),
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
        })

@app.route('/api/wifi/debug')
def wifi_debug():
    """API: WiFi掃描調試資訊"""
    try:
        import subprocess
        debug_info = {
            'system': platform.system(),
            'platform': sys.platform,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        if platform.system() == "Windows":
            # 測試基本的netsh命令
            try:
                result = subprocess.run(
                    ["netsh", "wlan", "show", "interfaces"],
                    capture_output=True,
                    text=True,
                    encoding='utf-8',
                    errors='ignore',
                    timeout=10
                )
                debug_info['interfaces_cmd'] = {
                    'returncode': result.returncode,
                    'stdout_length': len(result.stdout) if result.stdout else 0,
                    'stderr': result.stderr[:500] if result.stderr else None
                }
            except Exception as e:
                debug_info['interfaces_cmd_error'] = str(e)
            
            # 測試掃描命令
            try:
                result = subprocess.run(
                    ["netsh", "wlan", "show", "scan"],
                    capture_output=True,
                    text=True,
                    encoding='utf-8',
                    errors='ignore',
                    timeout=15
                )
                debug_info['scan_cmd'] = {
                    'returncode': result.returncode,
                    'stdout_length': len(result.stdout) if result.stdout else 0,
                    'stderr': result.stderr[:500] if result.stderr else None,
                    'stdout_preview': result.stdout[:1000] if result.stdout else None
                }
            except Exception as e:
                debug_info['scan_cmd_error'] = str(e)
        
        return jsonify({
            'success': True,
            'debug_info': debug_info
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'調試資訊獲取失敗: {str(e)}'
        })

@app.route('/api/wifi/connect', methods=['POST'])
def connect_wifi():
    """API: 連接到指定的WiFi網路"""
    try:
        data = request.get_json() or {}
        ssid = data.get('ssid', '').strip()
        password = data.get('password', '').strip()
        
        if not ssid:
            return jsonify({
                'success': False,
                'message': 'SSID不能為空'
            })
        
        # 嘗試連接WiFi
        success = network_checker.connect_to_wifi(ssid, password)
        
        if success:
            # 連接成功後，等待一段時間再檢查網路狀態
            import time
            time.sleep(3)
            
            # 重新檢查網路狀態
            network_status = network_checker.get_network_status()
            
            return jsonify({
                'success': True,
                'message': f'已成功連接到 {ssid}',
                'network_status': network_status
            })
        else:
            return jsonify({
                'success': False,
                'message': f'連接到 {ssid} 失敗，請檢查密碼是否正確'
            })
            
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'WiFi連接過程發生錯誤: {str(e)}'
        })

@app.route('/api/wifi/current')
def current_wifi():
    """API: 獲取當前連接的WiFi資訊"""
    try:
        current_wifi_info = network_checker.get_current_wifi_info()
        return jsonify({
            'success': True,
            'current_wifi': current_wifi_info
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'獲取當前WiFi資訊失敗: {str(e)}',
            'current_wifi': None
        })

@app.route('/host-config')
def host_config():
    """主機連接設定頁面"""
    try:
        # 獲取當前主機設定
        host_settings = config_manager.get('host_settings', {
            'target_host': 'localhost',
            'target_port': 8000,
            'connection_timeout': 10,
            'retry_attempts': 3,
            'protocol': 'HTTP'
        })
        
        return render_template('host_config.html', 
                             host_settings=host_settings,
                             page_title="主機連接設定")
    except Exception as e:
        flash(f'載入主機設定時發生錯誤: {str(e)}', 'danger')
        return redirect(url_for('index'))

@app.route('/api/host/save-config', methods=['POST'])
def save_host_config():
    """API: 儲存主機連接設定"""
    try:
        data = request.get_json() or {}
        
        # 驗證必要欄位
        required_fields = ['target_host', 'target_port']
        for field in required_fields:
            if not data.get(field):
                return jsonify({
                    'success': False,
                    'message': f'缺少必要欄位: {field}'
                })
        
        # 驗證端口範圍
        try:
            port = int(data['target_port'])
            if port < 1 or port > 65535:
                raise ValueError()
        except (ValueError, TypeError):
            return jsonify({
                'success': False,
                'message': '端口必須是1-65535之間的數字'
            })
        
        # 儲存設定
        host_settings = {
            'target_host': data['target_host'].strip(),
            'target_port': port,
            'connection_timeout': int(data.get('connection_timeout', 10)),
            'retry_attempts': int(data.get('retry_attempts', 3)),
            'protocol': data.get('protocol', 'HTTP')
        }
        
        config_manager.set('host_settings', host_settings)
        config_manager.save_config()
        
        return jsonify({
            'success': True,
            'message': '主機連接設定已儲存',
            'host_settings': host_settings
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'儲存主機設定失敗: {str(e)}'
        })

@app.route('/api/host/test-connection', methods=['POST'])
def test_host_connection():
    """API: 測試主機連接"""
    try:
        data = request.get_json() or {}
        host = data.get('host', 'localhost')
        port = int(data.get('port', 8000))
        timeout = int(data.get('timeout', 10))
        protocol = data.get('protocol', 'HTTP')
        
        # 測試連接
        success, message = test_connection_to_host(host, port, timeout, protocol)
        
        return jsonify({
            'success': success,
            'message': message,
            'connection_info': {
                'host': host,
                'port': port,
                'protocol': protocol,
                'tested_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'連接測試失敗: {str(e)}'
        })

def test_connection_to_host(host, port, timeout, protocol):
    """測試到指定主機的連接"""
    try:
        if protocol.upper() == 'HTTP':
            # HTTP連接測試
            import urllib.request
            import urllib.error
            
            url = f"http://{host}:{port}"
            try:
                req = urllib.request.Request(url, method='HEAD')
                with urllib.request.urlopen(req, timeout=timeout) as response:
                    return True, f"HTTP連接成功 - 狀態碼: {response.status}"
            except urllib.error.HTTPError as e:
                if e.code < 500:  # 4xx錯誤通常表示服務器在運行
                    return True, f"HTTP連接成功 - 狀態碼: {e.code}"
                else:
                    return False, f"HTTP連接失敗 - 狀態碼: {e.code}"
            except urllib.error.URLError:
                return False, f"HTTP連接失敗 - 無法連接到 {host}:{port}"
                
        elif protocol.upper() == 'HTTPS':
            # HTTPS連接測試
            import urllib.request
            import urllib.error
            import ssl
            
            # 創建不驗證SSL證書的context（用於測試）
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            
            url = f"https://{host}:{port}"
            try:
                req = urllib.request.Request(url, method='HEAD')
                with urllib.request.urlopen(req, timeout=timeout, context=ctx) as response:
                    return True, f"HTTPS連接成功 - 狀態碼: {response.status}"
            except urllib.error.HTTPError as e:
                if e.code < 500:
                    return True, f"HTTPS連接成功 - 狀態碼: {e.code}"
                else:
                    return False, f"HTTPS連接失敗 - 狀態碼: {e.code}"
            except urllib.error.URLError:
                return False, f"HTTPS連接失敗 - 無法連接到 {host}:{port}"
                
        else:
            # TCP連接測試
            import socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            
            result = sock.connect_ex((host, port))
            sock.close()
            
            if result == 0:
                return True, f"TCP連接成功 - 主機 {host}:{port} 可達"
            else:
                return False, f"TCP連接失敗 - 無法連接到 {host}:{port}"
                
    except Exception as e:
        return False, f"連接測試異常: {str(e)}"

# Dashboard 資料發送相關 API
@app.route('/api/dashboard-sender/status')
def get_dashboard_sender_status():
    """API: 獲取 Dashboard 資料發送狀態"""
    try:
        status = dashboard_sender.get_status()
        return jsonify({
            'success': True,
            'status': status
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'獲取狀態失敗: {str(e)}'
        })

@app.route('/api/dashboard-sender/config', methods=['GET', 'POST'])
def dashboard_sender_config():
    """API: 設定 Dashboard 資料發送配置"""
    if request.method == 'GET':
        try:
            return jsonify({
                'success': True,
                'config': {
                    'dashboard_url': dashboard_sender.dashboard_url,
                    'send_interval': dashboard_sender.send_interval,
                    'batch_size': dashboard_sender.batch_size,
                    'enabled': dashboard_sender.enabled
                }
            })
        except Exception as e:
            return jsonify({
                'success': False,
                'message': f'獲取配置失敗: {str(e)}'
            })
    
    elif request.method == 'POST':
        try:
            data = request.get_json()
            if not data:
                return jsonify({
                    'success': False,
                    'message': '無效的JSON資料'
                }), 400
            
            # 更新配置
            if 'dashboard_url' in data:
                dashboard_sender.set_dashboard_url(data['dashboard_url'])
            
            if 'send_interval' in data:
                dashboard_sender.send_interval = int(data['send_interval'])
            
            if 'batch_size' in data:
                dashboard_sender.batch_size = int(data['batch_size'])
            
            return jsonify({
                'success': True,
                'message': '配置已更新',
                'config': {
                    'dashboard_url': dashboard_sender.dashboard_url,
                    'send_interval': dashboard_sender.send_interval,
                    'batch_size': dashboard_sender.batch_size,
                    'enabled': dashboard_sender.enabled
                }
            })
            
        except Exception as e:
            return jsonify({
                'success': False,
                'message': f'更新配置失敗: {str(e)}'
            }), 500

@app.route('/api/dashboard-sender/start', methods=['POST'])
def start_dashboard_sender():
    """API: 啟動 Dashboard 資料發送服務"""
    try:
        if dashboard_sender.start():
            return jsonify({
                'success': True,
                'message': 'Dashboard 資料發送服務已啟動'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Dashboard 資料發送服務啟動失敗'
            })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'啟動服務失敗: {str(e)}'
        })

@app.route('/api/dashboard-sender/stop', methods=['POST'])
def stop_dashboard_sender():
    """API: 停止 Dashboard 資料發送服務"""
    try:
        if dashboard_sender.stop():
            return jsonify({
                'success': True,
                'message': 'Dashboard 資料發送服務已停止'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Dashboard 資料發送服務停止失敗'
            })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'停止服務失敗: {str(e)}'
        })

@app.route('/api/dashboard-sender/test', methods=['POST'])
def test_dashboard_connection():
    """API: 測試 Dashboard 連接"""
    try:
        # 發送測試資料
        test_data = {
            'mac_id': 'TEST:TEST:TEST',
            'channel': 0,
            'parameter': 99.9,
            'unit': 'TEST',
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        success, message = dashboard_sender.send_single_data(test_data)
        
        return jsonify({
            'success': success,
            'message': f'連接測試: {message}',
            'dashboard_url': dashboard_sender.dashboard_url
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'測試連接失敗: {str(e)}'
        })

if __name__ == '__main__':
    # Windows 編碼問題處理
    if os.name == 'nt':  # Windows 系統
        try:
            # 設定 UTF-8 編碼
            os.environ['PYTHONIOENCODING'] = 'utf-8'
            print("已設定 UTF-8 編碼環境")
        except Exception as encoding_error:
            print(f"設定編碼時發生警告: {encoding_error}")
    
    try:
        # 確保設定目錄存在
        if not os.path.exists('config'):
            os.makedirs('config')
        
        print("啟動動態協定設定系統...")
        print("支援的協定:", config_manager.get_supported_protocols())
        print("訪問 http://localhost:5000 開始使用")
        
        # 重置通訊協定設定為預設值，等待使用者設定
        default_cfg = config_manager._get_default_config()
        # 僅重置 protocols 區塊
        config_manager.config['protocols'] = default_cfg.get('protocols', {})
        # 移除已設定或啟用協定標記
        config_manager.config.pop('active_protocol', None)
        # 儲存更新後的配置
        config_manager.save_config()
        print("已重置通訊協定設定為預設值，請重新設定通訊協定並啟用。")
        
        # 啟動 Flask 應用程式
        app.run(debug=True, host='0.0.0.0', port=5000)
        
    except UnicodeDecodeError as unicode_error:
        print(f"發生編碼錯誤: {unicode_error}")
        print("提示：如果持續遇到編碼問題，請執行 'python start_app.py' 或設定環境變數 'set PYTHONIOENCODING=utf-8'")
        
    except Exception as e:
        print(f"啟動應用程式時發生錯誤: {e}")
        print("請檢查:")
        print("1. 相依套件是否已正確安裝 (pip install -r requirements.txt)")
        print("2. 端口 5000 是否被其他程式佔用")
        print("3. 網路設定是否正確") 