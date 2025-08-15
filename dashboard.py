"""
Dashboard API 服務
獨立的 Dashboard 和設備設定管理 API 服務
"""

from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, make_response, Response, session
from config_manager import ConfigManager
from uart_integrated import uart_reader, protocol_manager
from network_utils import network_checker, create_offline_mode_manager
from device_settings import DeviceSettingsManager
from multi_device_settings import MultiDeviceSettingsManager

# 導入資料庫管理器
try:
    from database_manager import db_manager
    DATABASE_AVAILABLE = True
    print("Dashboard: 資料庫管理器載入成功")
except ImportError as e:
    print(f"Dashboard: 資料庫管理器載入失敗: {e}")
    DATABASE_AVAILABLE = False
    db_manager = None

import os
import json
import logging
import platform
import sys
import time
import threading
import glob

# 修復 charset_normalizer 循環導入問題
import sys
if 'charset_normalizer' in sys.modules:
    del sys.modules['charset_normalizer']

# 安全導入 requests，避免 charset_normalizer 問題
requests = None
requests_available = False
try:
    import requests
    requests_available = True
except (ImportError, AttributeError) as e:
    print(f"requests 導入錯誤: {e}")
    print("嘗試使用替代方案...")
    try:
        # 清理可能有問題的模組
        modules_to_clean = ['charset_normalizer', 'urllib3']
        for module in modules_to_clean:
            if module in sys.modules:
                del sys.modules[module]
        
        # 重新嘗試導入
        import requests
        requests_available = True
        print("requests 重新導入成功")
    except Exception as e2:
        print(f"requests 無法導入: {e2}")
        print("將使用 urllib 作為替代方案")
        requests = None
        requests_available = False

# 無論如何都要導入 urllib 作為備選
import urllib.request
import urllib.parse
import urllib.error

from datetime import datetime, timedelta

# 嘗試導入 psutil，如果沒有安裝則跳過
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    print("psutil 未安裝，系統監控功能將受限，可以執行 'pip install psutil' 來安裝")

# 設定日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] [Dashboard] %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

# 建立 Flask 應用程式
app = Flask(__name__)
app.secret_key = 'dashboard_secret_key_2025'

# 樹莓派 API 配置 - 支援動態配置
RASPBERRY_PI_CONFIG = {
    'host': '192.168.113.239',  # 預設IP地址
    'port': 5000,
    'timeout': 10,
    'auto_discover': True,      # 是否啟用自動發現
    'backup_hosts': [           # 備用IP地址列表
        '192.168.1.100',
        '192.168.50.1', 
        '10.0.0.100'
    ]
}

def get_raspberry_pi_url():
    """取得樹莓派 API 基礎 URL"""
    return f"http://{RASPBERRY_PI_CONFIG['host']}:{RASPBERRY_PI_CONFIG['port']}"

def discover_raspberry_pi():
    """自動發現樹莓派設備"""
    import socket
    import threading
    from concurrent.futures import ThreadPoolExecutor, as_completed
    
    discovered_devices = []
    
    def check_host(ip):
        """檢查單個IP地址是否為樹莓派"""
        try:
            # 嘗試連接到可能的樹莓派端點
            test_endpoints = [
                f"http://{ip}:{RASPBERRY_PI_CONFIG['port']}/api/health",
                f"http://{ip}:{RASPBERRY_PI_CONFIG['port']}/api/status",
                f"http://{ip}:{RASPBERRY_PI_CONFIG['port']}/api/uart/status"
            ]
            
            for endpoint in test_endpoints:
                try:
                    if requests_available:
                        response = requests.get(endpoint, timeout=3)
                        if response.status_code == 200:
                            data = response.json()
                            return {
                                'ip': ip,
                                'port': RASPBERRY_PI_CONFIG['port'],
                                'status': 'online',
                                'endpoint': endpoint,
                                'response': data
                            }
                    else:
                        # 使用urllib作為備選
                        req = urllib.request.Request(endpoint)
                        response = urllib.request.urlopen(req, timeout=3)
                        if response.getcode() == 200:
                            return {
                                'ip': ip,
                                'port': RASPBERRY_PI_CONFIG['port'],
                                'status': 'online',
                                'endpoint': endpoint,
                                'response': {}
                            }
                except:
                    continue
            return None
        except Exception:
            return None
    
    # 獲取當前網路段
    try:
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
        network_base = '.'.join(local_ip.split('.')[:-1])
        
        # 要掃描的IP列表
        ips_to_scan = []
        
        # 添加當前網路段的常見IP
        for i in range(100, 200):  # 掃描 x.x.x.100-199
            ips_to_scan.append(f"{network_base}.{i}")
        
        # 添加備用主機列表
        ips_to_scan.extend(RASPBERRY_PI_CONFIG.get('backup_hosts', []))
        
        # 添加當前配置的主機
        if RASPBERRY_PI_CONFIG['host'] not in ips_to_scan:
            ips_to_scan.insert(0, RASPBERRY_PI_CONFIG['host'])
        
        logging.info(f"開始自動發現樹莓派，掃描 {len(ips_to_scan)} 個IP地址...")
        
        # 使用線程池並行掃描
        with ThreadPoolExecutor(max_workers=20) as executor:
            future_to_ip = {executor.submit(check_host, ip): ip for ip in ips_to_scan}
            
            for future in as_completed(future_to_ip, timeout=15):
                result = future.result()
                if result:
                    discovered_devices.append(result)
                    logging.info(f"發現樹莓派: {result['ip']}")
        
        logging.info(f"自動發現完成，找到 {len(discovered_devices)} 個樹莓派設備")
        return discovered_devices
        
    except Exception as e:
        logging.error(f"自動發現樹莓派時發生錯誤: {e}")
        return []

def auto_connect_raspberry_pi():
    """自動連接到可用的樹莓派"""
    global RASPBERRY_PI_CONFIG
    
    if not RASPBERRY_PI_CONFIG.get('auto_discover', True):
        return test_raspberry_pi_connection()
    
    # 首先測試當前配置的主機
    current_status = test_raspberry_pi_connection()
    if current_status['connected']:
        return current_status
    
    # 如果當前主機不可用，嘗試自動發現
    logging.info("當前樹莓派無法連接，開始自動發現...")
    discovered = discover_raspberry_pi()
    
    if discovered:
        # 選擇第一個可用的設備
        best_device = discovered[0]
        old_host = RASPBERRY_PI_CONFIG['host']
        RASPBERRY_PI_CONFIG['host'] = best_device['ip']
        
        logging.info(f"自動切換樹莓派地址：{old_host} -> {best_device['ip']}")
        
        return {
            'connected': True,
            'message': f'自動發現並連接到樹莓派 {best_device["ip"]}',
            'auto_discovered': True,
            'previous_host': old_host,
            'discovered_devices': len(discovered)
        }
    else:
        return {
            'connected': False,
            'message': '無法發現任何可用的樹莓派設備',
            'auto_discovered': False,
            'discovered_devices': 0
        }

def call_raspberry_pi_api(endpoint, method='GET', data=None, timeout=None):
    """調用樹莓派 API"""
    if timeout is None:
        timeout = RASPBERRY_PI_CONFIG['timeout']
    
    url = f"{get_raspberry_pi_url()}{endpoint}"
    
    # 優先使用 requests，如果不可用則使用 urllib
    if requests_available:
        try:
            if method.upper() == 'GET':
                response = requests.get(url, timeout=timeout)
            elif method.upper() == 'POST':
                response = requests.post(url, json=data, timeout=timeout)
            else:
                response = requests.request(method, url, json=data, timeout=timeout)
            
            if response.status_code == 200:
                return True, response.json()
            else:
                return False, {'error': f'HTTP {response.status_code}: {response.text}'}
        
        except requests.exceptions.Timeout:
            return False, {'error': f'連接超時 (>{timeout}秒)'}
        except requests.exceptions.ConnectionError:
            return False, {'error': '無法連接到樹莓派，請檢查網路連線和樹莓派 IP 地址'}
        except requests.exceptions.RequestException as e:
            return False, {'error': f'請求錯誤: {str(e)}'}
        except Exception as e:
            return False, {'error': f'未知錯誤: {str(e)}'}
    
    else:
        # 使用 urllib 作為備選方案
        try:
            import urllib.request
            import urllib.error
            import urllib.parse
            import json
            
            if method.upper() == 'GET':
                req = urllib.request.Request(url)
            elif method.upper() == 'POST':
                req_data = json.dumps(data).encode('utf-8') if data else None
                req = urllib.request.Request(url, data=req_data)
                req.add_header('Content-Type', 'application/json')
            else:
                req_data = json.dumps(data).encode('utf-8') if data else None
                req = urllib.request.Request(url, data=req_data, method=method)
                req.add_header('Content-Type', 'application/json')
            
            response = urllib.request.urlopen(req, timeout=timeout)
            response_text = response.read().decode('utf-8')
            return True, json.loads(response_text)
            
        except urllib.error.HTTPError as e:
            return False, {'error': f'HTTP {e.code}: {e.reason}'}
        except urllib.error.URLError as e:
            return False, {'error': '無法連接到樹莓派，請檢查網路連線和樹莓派 IP 地址'}
        except Exception as e:
            return False, {'error': f'未知錯誤: {str(e)}'}

# 初始化管理器
config_manager = ConfigManager()
device_settings_manager = DeviceSettingsManager()
multi_device_settings_manager = MultiDeviceSettingsManager()

# 初始化離線模式管理器
offline_mode_manager = create_offline_mode_manager(config_manager)

# 啟動時自動偵測網路狀態和樹莓派連接
network_mode = offline_mode_manager.auto_detect_mode()
logging.info(f"系統啟動模式: {network_mode}")

# 樹莓派連接將在函數定義後進行初始化

# 全域變數暫存模式
current_mode = {'mode': 'idle'}

# 樹莓派配置管理
@app.route('/api/raspberry-pi-config', methods=['GET', 'POST'])
def raspberry_pi_config():
    """樹莓派連接配置"""
    global RASPBERRY_PI_CONFIG
    
    if request.method == 'GET':
        return jsonify({
            'success': True,
            'config': RASPBERRY_PI_CONFIG,
            'status': test_raspberry_pi_connection()
        })
    
    elif request.method == 'POST':
        try:
            data = request.get_json()
            if not data:
                return jsonify({'success': False, 'message': '無效的JSON數據'})
            
            # 更新配置
            if 'host' in data:
                RASPBERRY_PI_CONFIG['host'] = data['host']
            if 'port' in data:
                RASPBERRY_PI_CONFIG['port'] = int(data['port'])
            if 'timeout' in data:
                RASPBERRY_PI_CONFIG['timeout'] = int(data['timeout'])
            if 'auto_discover' in data:
                RASPBERRY_PI_CONFIG['auto_discover'] = bool(data['auto_discover'])
            if 'backup_hosts' in data:
                RASPBERRY_PI_CONFIG['backup_hosts'] = data['backup_hosts']
            
            # 測試連接
            status = test_raspberry_pi_connection()
            
            return jsonify({
                'success': True,
                'message': '配置已更新',
                'config': RASPBERRY_PI_CONFIG,
                'status': status
            })
            
        except Exception as e:
            return jsonify({
                'success': False,
                'message': f'更新配置失敗: {str(e)}'
            })

@app.route('/api/raspberry-pi-discover', methods=['POST'])
def raspberry_pi_discover():
    """手動觸發樹莓派自動發現"""
    try:
        discovered = discover_raspberry_pi()
        return jsonify({
            'success': True,
            'discovered_devices': discovered,
            'device_count': len(discovered),
            'message': f'發現 {len(discovered)} 個樹莓派設備'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'自動發現失敗: {str(e)}',
            'discovered_devices': []
        })

@app.route('/api/raspberry-pi-auto-connect', methods=['POST'])
def raspberry_pi_auto_connect():
    """自動連接到可用的樹莓派"""
    try:
        result = auto_connect_raspberry_pi()
        return jsonify({
            'success': result['connected'],
            'result': result
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'自動連接失敗: {str(e)}'
        })

def test_raspberry_pi_connection():
    """測試樹莓派連接"""
    try:
        # 嘗試多個端點來測試連接
        test_endpoints = ['/api/health', '/api/status', '/api/data', '/']
        
        for endpoint in test_endpoints:
            success, result = call_raspberry_pi_api(endpoint, timeout=5)
            if success:
                return {
                    'connected': True,
                    'message': f'連接正常 (通過 {endpoint} 端點)',
                    'response_time': '< 5秒'
                }
        
        # 如果所有API端點都失敗，嘗試簡單的HTTP連接測試
        try:
            import urllib.request
            url = get_raspberry_pi_url()
            response = urllib.request.urlopen(url, timeout=5)
            if response.getcode() in [200, 404, 500]:  # 任何HTTP回應都表示連接成功
                return {
                    'connected': True,
                    'message': '連接正常 (HTTP連接成功)',
                    'response_time': '< 5秒'
                }
        except Exception:
            pass
            
        return {
            'connected': False,
            'message': '無法連接到樹莓派，請檢查IP地址和網路連線',
            'response_time': 'N/A'
        }
    except Exception as e:
        return {
            'connected': False,
            'message': f'連接測試失敗: {str(e)}',
            'response_time': 'N/A'
        }

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

# 工具函數
def get_system_info():
    """獲取系統基本資訊"""
    return {
        'platform': platform.system(),
        'platform_version': platform.release(),
        'python_version': platform.python_version(),
        'working_directory': os.getcwd(),
        'psutil_available': PSUTIL_AVAILABLE
    }

def safe_get_uart_data():
    """安全地獲取UART數據"""
    try:
        if uart_reader and hasattr(uart_reader, 'get_latest_data'):
            return uart_reader.get_latest_data()
        return []
    except Exception as e:
        logging.warning(f"獲取UART數據時發生錯誤: {e}")
        return []

def get_uart_data_from_files(mac_id=None, limit=10000):
    """從History資料夾的CSV文件中讀取UART數據"""
    import csv
    import glob
    
    try:
        # 獲取當前目錄下的History資料夾
        current_dir = os.path.dirname(os.path.abspath(__file__))
        history_dir = os.path.join(current_dir, 'History')
        
        if not os.path.exists(history_dir):
            return {
                'success': False,
                'error': 'History資料夾不存在',
                'data': []
            }
        
        # 尋找所有的uart_data_*.csv文件
        csv_pattern = os.path.join(history_dir, 'uart_data_*.csv')
        csv_files = glob.glob(csv_pattern)
        
        if not csv_files:
            return {
                'success': False,
                'error': '沒有找到UART數據文件',
                'data': []
            }
        
        # 按檔案名稱排序，最新的在最後
        csv_files.sort()
        
        all_data = []
        total_count = 0
        
        # 讀取最近的文件數據（優先讀取今天的文件，確保獲取最新數據）
        today_file = f"uart_data_{datetime.now().strftime('%Y%m%d')}.csv"
        priority_files = []
        other_files = []
        
        for csv_file in csv_files[-5:]:  # 只讀取最近5個文件
            filename = os.path.basename(csv_file)
            if filename == today_file:
                priority_files.insert(0, csv_file)  # 今天的文件優先
            else:
                other_files.append(csv_file)
        
        # 合併文件列表，今天的文件在前
        files_to_read = priority_files + other_files[-2:]  # 最多讀取3個文件
        
        for csv_file in files_to_read:
            try:
                with open(csv_file, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    file_data = []
                    for row in reader:
                        # 轉換數據格式以匹配原來的結構
                        try:
                            data_entry = {
                                'timestamp': row.get('timestamp', ''),
                                'mac_id': row.get('mac_id', 'N/A'),
                                'channel': int(row.get('channel', 0)) if row.get('channel', '').isdigit() else 0,
                                'parameter': float(row.get('parameter', 0)) if row.get('parameter', '').replace('.', '').replace('-', '').isdigit() else 0,
                                'unit': row.get('unit', 'N/A')
                            }
                            file_data.append(data_entry)
                            total_count += 1
                        except (ValueError, TypeError) as e:
                            continue  # 跳過無效的行
                    
                    all_data.extend(file_data)
                    logging.debug(f"📁 從 {os.path.basename(csv_file)} 讀取了 {len(file_data)} 筆數據")
                    
            except Exception as e:
                logging.warning(f"⚠️  讀取文件 {csv_file} 時發生錯誤: {e}")
                continue
        
        # 按時間戳排序，最新的在最後
        all_data.sort(key=lambda x: x.get('timestamp', ''))
        
        # 如果指定了limit，只取最近的數據
        if limit and len(all_data) > limit:
            all_data = all_data[-limit:]
        
        # 按通道分組數據
        channels_data = {}
        for entry in all_data:
            # 如果指定了特定MAC ID，只返回該設備的數據
            if mac_id is not None and entry.get('mac_id') != mac_id:
                continue
                
            channel_num = entry.get('channel', 0)
            if channel_num not in channels_data:
                channels_data[channel_num] = {
                    'channel': channel_num,
                    'unit': entry.get('unit', 'N/A'),
                    'mac_id': entry.get('mac_id', 'N/A'),
                    'data': []
                }
            
            channels_data[channel_num]['data'].append({
                'timestamp': entry.get('timestamp'),
                'parameter': entry.get('parameter', 0),
                'mac_id': entry.get('mac_id', 'N/A')
            })
        
        # 轉換為列表格式並按通道排序
        result_data = list(channels_data.values())
        result_data.sort(key=lambda x: x['channel'])
        
        logging.info(f"從CSV文件讀取 - 通道數: {len(result_data)}, 總數據點: {sum(len(ch['data']) for ch in result_data)}")
        
        return {
            'success': True,
            'data': result_data,
            'total_files': len(csv_files),
            'total_raw_count': total_count
        }
        
    except Exception as e:
        logging.error(f"從文件讀取UART數據時發生錯誤: {e}")
        return {
            'success': False,
            'error': f'讀取數據時發生錯誤: {str(e)}',
            'data': []
        }

def get_system_stats():
    """獲取系統統計資訊"""
    if PSUTIL_AVAILABLE:
        try:
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
                
            return {
                'cpu_percent': cpu_percent,
                'memory_percent': memory_percent,
                'disk_percent': disk_percent,
                'network_sent': network_sent,
                'network_recv': network_recv,
            }
        except Exception as psutil_error:
            logging.error(f"獲取系統統計時發生錯誤: {psutil_error}")
            return {
                'cpu_percent': 0,
                'memory_percent': 0,
                'disk_percent': 0,
                'network_sent': 0,
                'network_recv': 0,
            }
    else:
        return {
            'cpu_percent': 0,
            'memory_percent': 0,
            'disk_percent': 0,
            'network_sent': 0,
            'network_recv': 0,
        }

def get_detailed_system_info():
    """獲取詳細的系統監控資訊"""
    if PSUTIL_AVAILABLE:
        try:
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
                
            return {
                'cpu_percent': cpu_percent,
                'memory': memory_info,
                'disk': disk_info,
                'network': network_info,
                'boot_time': boot_time
            }
        except Exception as psutil_error:
            logging.error(f"獲取系統資訊時發生錯誤: {psutil_error}")
            return {
                'cpu_percent': 'N/A (系統資訊獲取失敗)',
                'memory': {'percent': 0},
                'disk': {'percent': 0},
                'network': {},
                'boot_time': 'N/A'
            }
    else:
        return {
            'cpu_percent': 'N/A (需要安裝 psutil)',
            'memory': {'percent': 0},
            'disk': {'percent': 0},
            'network': {},
            'boot_time': 'N/A'
        }

# ====== 設備設定相關路由 ======

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

@app.route('/api/dashboard/areas')
def api_dashboard_areas():
    """API: 獲取所有廠區、位置、設備型號統計資料"""
    try:
        all_devices = multi_device_settings_manager.load_all_devices()
        
        # 統計廠區 (device_name)
        areas = set()
        locations = set()
        models = set()
        
        for mac_id, device_setting in all_devices.items():
            # 廠區對應 device_name
            if device_setting.get('device_name'):
                areas.add(device_setting['device_name'])
            
            # 設備位置對應 device_location    
            if device_setting.get('device_location'):
                locations.add(device_setting['device_location'])
            
            # 設備型號處理
            device_model = device_setting.get('device_model', '')
            if isinstance(device_model, dict):
                # 如果是字典格式（多頻道型號）
                for channel, model in device_model.items():
                    if model and model.strip():
                        models.add(model.strip())
            elif isinstance(device_model, str) and device_model.strip():
                models.add(device_model.strip())
        
        return jsonify({
            'success': True,
            'areas': sorted(list(areas)),
            'locations': sorted(list(locations)),
            'models': sorted(list(models)),
            'device_count': len(all_devices),
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logging.error(f"獲取廠區統計資料時發生錯誤: {e}")
        return jsonify({
            'success': False,
            'message': f'獲取廠區統計資料失敗: {str(e)}',
            'areas': [],
            'locations': [],
            'models': []
        })

# ====== Dashboard 相關路由 ======

@app.route('/dashboard')
def flask_dashboard():
    """Flask Dashboard 主頁面"""
    logging.info(f'訪問Flask Dashboard, remote_addr={request.remote_addr}')
    
    # 檢查設備設定是否完成
    if not device_settings_manager.is_configured():
        logging.info("設備尚未設定，重定向到設定頁面")
        flash('請先完成設備設定', 'warning')
        return redirect(url_for('db_setting', redirect='true'))
    
    # 測試樹莓派連接
    pi_status = test_raspberry_pi_connection()
    
    # 提供基本的系統監控資訊
    system_info = get_detailed_system_info()
    
    # 應用程式統計 (本地)
    app_stats = {
        'uart_running': False,
        'uart_data_count': 0,
        'active_protocol': 'N/A (連接樹莓派)',
        'offline_mode': not pi_status['connected'],
        'raspberry_pi_status': pi_status,
        'raspberry_pi_ip': RASPBERRY_PI_CONFIG['host']
    }
    
    return render_template('dashboard.html',
                         system_info=system_info,
                         app_stats=app_stats,
                         raspberry_pi_config=RASPBERRY_PI_CONFIG,
                         pi_status=pi_status)

@app.route('/data-analysis')
def data_analysis():
    """資料分析頁面"""
    logging.info(f'訪問資料分析頁面, remote_addr={request.remote_addr}')
    
    # 檢查資料庫是否可用
    if not DATABASE_AVAILABLE or not db_manager:
        flash('資料庫功能未啟用，請檢查系統配置', 'error')
        return redirect(url_for('flask_dashboard'))
    
    return render_template('data_analysis.html')

@app.route('/raspberry-pi-config')
def raspberry_pi_config_page():
    """樹莓派連接配置頁面"""
    logging.info(f'訪問樹莓派配置頁面, remote_addr={request.remote_addr}')
    
    # 測試當前連接狀態
    pi_status = test_raspberry_pi_connection()
    
    return render_template('raspberry_pi_config.html',
                         config=RASPBERRY_PI_CONFIG,
                         status=pi_status)

@app.route('/11')
def dashboard_11():
    """儀表板總覽頁面 (11.html)"""
    logging.info(f'訪問儀表板總覽頁面 11.html, remote_addr={request.remote_addr}')
    return render_template('11.html')

@app.route('/api/dashboard/stats')
def dashboard_stats():
    """API: 獲取 Dashboard 統計資料 (從樹莓派)"""
    try:
        # 嘗試從樹莓派獲取統計資料
        success, pi_data = call_raspberry_pi_api('/api/dashboard/stats')
        
        if success:
            # 成功從樹莓派獲取數據
            pi_data['source'] = '樹莓派'
            pi_data['raspberry_pi_ip'] = RASPBERRY_PI_CONFIG['host']
            pi_data['connection_status'] = '已連接'
            return jsonify(pi_data)
        else:
            # 無法連接樹莓派，使用本地數據
            logging.warning(f"無法從樹莓派獲取數據: {pi_data.get('error', '未知錯誤')}")
            
            # 本地系統資源資訊
            system_stats = get_system_stats()
            
            # 應用程式統計 (本地)
            app_stats = {
                'uart_running': False,
                'uart_data_count': 0,
                'active_protocol': 'N/A (離線模式)',
                'offline_mode': True,
                'current_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            }
            
            # 載入設備設定 (本地)
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
                'timestamp': datetime.now().isoformat(),
                'source': '本地 (離線模式)',
                'raspberry_pi_ip': RASPBERRY_PI_CONFIG['host'],
                'connection_status': '離線',
                'connection_error': pi_data.get('error', '連接失敗')
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
            },
            'device_settings': {
                'device_name': '未設定設備',
                'device_location': '',
                'device_model': '',
                'device_serial': '',
                'device_description': ''
            },
            'source': '錯誤',
            'raspberry_pi_ip': RASPBERRY_PI_CONFIG['host'],
            'connection_status': '錯誤'
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
    """API: 獲取圖表數據 (從樹莓派)"""
    try:
        # 獲取查詢參數
        limit = request.args.get('limit', 50000, type=int)
        channel = request.args.get('channel', None, type=int)
        mac_id = request.args.get('mac_id', None)
        
        # 構建樹莓派 API 查詢參數
        params = f"?limit={limit}"
        if channel is not None:
            params += f"&channel={channel}"
        if mac_id is not None:
            params += f"&mac_id={mac_id}"
        
        # 嘗試從樹莓派獲取圖表數據
        success, pi_data = call_raspberry_pi_api(f'/api/dashboard/chart-data{params}')
        
        if success:
            # 成功從樹莓派獲取數據
            pi_data['source'] = '樹莓派'
            pi_data['raspberry_pi_ip'] = RASPBERRY_PI_CONFIG['host']
            logging.info(f"從樹莓派獲取圖表數據成功 - {len(pi_data.get('data', []))} 個通道")
            return jsonify(pi_data)
        else:
            # 無法連接樹莓派，使用本地數據
            logging.warning(f"無法從樹莓派獲取圖表數據: {pi_data.get('error', '未知錯誤')}")
            
            # 記錄 API 請求
            logging.info(f"圖表數據請求 (本地模式) - limit={limit}, channel={channel}, mac_id={mac_id}")
            
            # 直接從本地CSV文件讀取數據
            raw_data = []
            
            try:
                file_data = get_uart_data_from_files(mac_id, limit)
                if file_data.get('success'):
                    # 轉換文件格式到 raw_data 格式
                    for channel_data in file_data.get('data', []):
                        for data_point in channel_data.get('data', []):
                            raw_data.append({
                                'timestamp': data_point.get('timestamp'),
                                'mac_id': channel_data.get('mac_id', 'N/A'),
                                'channel': channel_data.get('channel', 0),
                                'parameter': data_point.get('parameter'),
                                'unit': channel_data.get('unit', 'N/A')
                            })
                    logging.debug(f"從本地CSV文件讀取到 {len(raw_data)} 筆數據")
                else:
                    logging.warning(f"從本地CSV文件讀取數據失敗: {file_data.get('error', '未知錯誤')}")
            except Exception as e:
                logging.error(f"從本地CSV文件讀取數據時發生錯誤: {e}")
            
            # 如果沒有數據，返回空結果
            if len(raw_data) == 0:
                return jsonify({
                    'success': True,
                    'data': [],
                    'total_channels': 0,
                    'filtered_by_mac_id': mac_id,
                    'data_source': '本地CSV文件 (無數據)',
                    'source': '本地 (離線模式)',
                    'raspberry_pi_ip': RASPBERRY_PI_CONFIG['host'],
                    'connection_error': pi_data.get('error', '連接失敗'),
                    'timestamp': datetime.now().isoformat()
                })
            
            # 處理本地數據 (簡化版本)
            chart_data = {}
            
            # 限制數據量
            if len(raw_data) > limit:
                raw_data = raw_data[-limit:]
            
            # 處理數據
            for entry in raw_data:
                entry_channel = entry.get('channel', 0)
                entry_mac_id = entry.get('mac_id', 'N/A')
                
                # 過濾條件
                if channel is not None and entry_channel != channel:
                    continue
                if mac_id is not None and entry_mac_id != mac_id:
                    continue
                
                # 建立通道數據結構
                if entry_channel not in chart_data:
                    chart_data[entry_channel] = {
                        'channel': entry_channel,
                        'unit': entry.get('unit', 'N/A'),
                        'mac_id': entry_mac_id,
                        'data': []
                    }
                
                # 添加數據點
                chart_data[entry_channel]['data'].append({
                    'timestamp': entry.get('timestamp'),
                    'parameter': entry.get('parameter'),
                    'mac_id': entry_mac_id
                })
            
            # 轉換為列表格式
            result_data = list(chart_data.values())
            
            return jsonify({
                'success': True,
                'data': result_data,
                'total_channels': len(result_data),
                'filtered_by_mac_id': mac_id,
                'data_source': '本地CSV文件',
                'source': '本地 (離線模式)',
                'raspberry_pi_ip': RASPBERRY_PI_CONFIG['host'],
                'connection_error': pi_data.get('error', '連接失敗'),
                'timestamp': datetime.now().isoformat()
            })
        
    except Exception as e:
        logging.error(f"獲取圖表數據時發生錯誤: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'獲取圖表數據失敗: {str(e)}',
            'data': [],
            'total_channels': 0,
            'source': '錯誤',
            'raspberry_pi_ip': RASPBERRY_PI_CONFIG['host'],
            'timestamp': datetime.now().isoformat()
        })
        
@app.route('/api/dashboard/devices')
def dashboard_devices():
    """API: 獲取所有設備列表 (從樹莓派)"""
    try:
        # 嘗試從樹莓派獲取設備列表
        success, pi_data = call_raspberry_pi_api('/api/dashboard/devices')
        
        if success:
            # 成功從樹莓派獲取數據
            pi_data['source'] = '樹莓派'
            pi_data['raspberry_pi_ip'] = RASPBERRY_PI_CONFIG['host']
            return jsonify(pi_data)
        else:
            # 無法連接樹莓派，返回空設備列表
            logging.warning(f"無法從樹莓派獲取設備列表: {pi_data.get('error', '未知錯誤')}")
            
            return jsonify({
                'success': True,
                'devices': [],
                'total_devices': 0,
                'source': '本地 (離線模式)',
                'raspberry_pi_ip': RASPBERRY_PI_CONFIG['host'],
                'connection_error': pi_data.get('error', '連接失敗'),
                'message': '無法連接到樹莓派，請檢查網路連線',
                'timestamp': datetime.now().isoformat()
            })
        
    except Exception as e:
        logging.error(f"獲取設備列表時發生錯誤: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'獲取設備列表失敗: {str(e)}',
            'devices': [],
            'source': '錯誤',
            'raspberry_pi_ip': RASPBERRY_PI_CONFIG['host']
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

# ====== 健康檢查和狀態 API ======

@app.route('/api/health')
def health_check():
    """健康檢查 API"""
    return jsonify({
        'status': 'healthy',
        'service': 'Dashboard API',
        'timestamp': datetime.now().isoformat(),
        'system_info': get_system_info()
    })

@app.route('/api/status')
def status():
    """服務狀態 API"""
    try:
        return jsonify({
            'success': True,
            'service': 'Dashboard API',
            'version': '1.0.0',
            'uptime': datetime.now().isoformat(),
            'psutil_available': PSUTIL_AVAILABLE,
            'uart_connection': uart_reader.is_running if uart_reader else False,
            'device_configured': device_settings_manager.is_configured()
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'狀態檢查失敗: {str(e)}'
        })

@app.route('/api/uart/status')
def uart_status():
    """API: 獲取UART狀態"""
    try:
        # 從CSV文件獲取數據狀態
        data_info = get_uart_data_from_files()
        
        # 檢查 uart_reader 是否可用
        if 'uart_reader' in globals():
            return jsonify({
                'success': True,
                'is_running': uart_reader.is_running,
                'data_count': data_info.get('total_raw_count', 0),
                'channels': len(data_info.get('data', [])),
                'has_data': data_info.get('success', False)
            })
        else:
            # 即使 uart_reader 不可用，也從文件獲取狀態
            return jsonify({
                'success': True,
                'is_running': False,
                'data_count': data_info.get('total_raw_count', 0),
                'channels': len(data_info.get('data', [])),
                'has_data': data_info.get('success', False)
            })
    except Exception as e:
        logging.error(f'獲取UART狀態時發生錯誤: {str(e)}')
        return jsonify({
            'success': False, 
            'message': f'獲取UART狀態時發生錯誤: {str(e)}'
        })

@app.route('/api/uart/mac-ids', methods=['GET'])
def get_uart_mac_ids():
    """API: 獲取UART接收到的MAC ID列表"""
    try:
        # 記錄 API 請求
        logging.info(f'API請求: /api/uart/mac-ids from {request.remote_addr}')
        
        # 優先嘗試從 uart_reader 獲取數據
        data = []
        data_source = "直接讀取"
        
        if uart_reader and hasattr(uart_reader, 'get_latest_data'):
            try:
                data = uart_reader.get_latest_data()
                logging.info(f'UART數據總數: {len(data) if data else 0}')
                data_source = 'UART即時數據'
                
                # 修正：如果即時數據為空或MAC ID數量少於預期，強制載入歷史數據
                if not data or len(set(entry.get('mac_id') for entry in data if entry.get('mac_id') and entry.get('mac_id') not in ['N/A', '', None])) < 1:
                    logging.info('即時數據不足，嘗試從歷史文件載入MAC ID')
                    if hasattr(uart_reader, 'load_historical_data'):
                        uart_reader.load_historical_data(days_back=7)  # 載入最近7天的數據
                        data = uart_reader.get_latest_data()
                        data_source = '歷史文件增強載入'
                        logging.info(f'從歷史文件增強載入數據: {len(data) if data else 0} 筆')
            except Exception as e:
                logging.warning(f"從uart_reader獲取數據失敗: {e}")
                data = []
        
        # 如果沒有即時數據，嘗試從文件獲取
        if not data:
            logging.info("嘗試從History文件獲取數據")
            data_info = get_uart_data_from_files()
            if data_info.get('success'):
                # 從分組的通道數據中提取所有原始數據
                data = []
                for channel_data in data_info.get('data', []):
                    for data_point in channel_data.get('data', []):
                        data.append({
                            'mac_id': channel_data.get('mac_id', 'N/A'),
                            'channel': channel_data.get('channel', 0),
                            'timestamp': data_point.get('timestamp'),
                            'parameter': data_point.get('parameter'),
                            'unit': channel_data.get('unit', 'N/A')
                        })
                data_source = "歷史文件"
                logging.info(f'從文件獲取到 {len(data)} 筆數據')
            else:
                logging.warning(f"從文件獲取數據失敗: {data_info.get('error', '未知錯誤')}")
        
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
                mac_ids.append(mac_id)
                valid_mac_count += 1
        
        # 去重複並排序
        unique_mac_ids = sorted(list(set(mac_ids)))
        
        # 記錄處理結果
        logging.info(f'MAC ID 處理結果: 總數據{len(data)}, 有效MAC數據{valid_mac_count}, 唯一MAC ID數{len(unique_mac_ids)}')
        if unique_mac_ids:
            logging.info(f'找到的 MAC IDs: {unique_mac_ids}')
        
        return jsonify({
            'success': True,
            'mac_ids': unique_mac_ids,
            'total_records': len(data),
            'valid_mac_records': valid_mac_count,
            'unique_mac_count': len(unique_mac_ids),
            'data_source': data_source,
            'timestamp': datetime.now().isoformat(),
            'message': f'找到 {len(unique_mac_ids)} 個唯一的 MAC ID (來源: {data_source})'
        })
        
    except Exception as e:
        error_msg = f'獲取MAC ID列表時發生錯誤: {str(e)}'
        logging.error(error_msg)
        return jsonify({
            'success': False, 
            'message': error_msg,
            'mac_ids': [],
            'timestamp': datetime.now().isoformat()
        })

@app.route('/api/uart/mac-channels/', methods=['GET'])
@app.route('/api/uart/mac-channels/<mac_id>', methods=['GET'])
def get_uart_mac_channels(mac_id=None):
    """API: 獲取指定MAC ID的通道資訊，或所有MAC ID的通道統計"""
    try:
        # 優先嘗試從 uart_reader 獲取數據
        data = []
        data_source = "直接讀取"
        
        if 'uart_reader' in globals() and uart_reader and hasattr(uart_reader, 'get_latest_data'):
            try:
                data = uart_reader.get_latest_data()
                if data:
                    data_source = "即時數據"
            except Exception as e:
                logging.warning(f"從uart_reader獲取數據失敗: {e}")
        
        # 如果沒有即時數據，嘗試從文件獲取
        if not data:
            logging.info("嘗試從History文件獲取通道數據")
            data_info = get_uart_data_from_files()
            if data_info.get('success'):
                # 從分組的通道數據中提取所有原始數據
                data = []
                for channel_data in data_info.get('data', []):
                    for data_point in channel_data.get('data', []):
                        data.append({
                            'mac_id': data_point.get('mac_id', channel_data.get('mac_id', 'N/A')),
                            'channel': channel_data.get('channel', 0),
                            'timestamp': data_point.get('timestamp'),
                            'parameter': data_point.get('parameter'),
                            'unit': channel_data.get('unit', 'A')
                        })
                data_source = "歷史文件"
                logging.info(f"從歷史文件載入了 {len(data)} 筆原始數據")
            else:
                logging.warning(f"從文件獲取數據失敗: {data_info.get('error', '未知錯誤')}")

        if not data:
            return jsonify({
                'success': True, 
                'data': [], 
                'message': '暫無UART數據，請先啟動UART讀取或檢查數據文件'
            })

        logging.info(f"總共處理 {len(data)} 筆UART數據，來源: {data_source}")

        if mac_id:
            # 如果請求特定MAC ID，返回該MAC ID的時間序列數據
            mac_data_points = []
            
            for entry in data:
                entry_mac_id = entry.get('mac_id', 'N/A')
                if entry_mac_id == mac_id:
                    # 只取電流頻道的數據（頻道0-6，排除頻道7電池電壓）
                    entry_channel = entry.get('channel', 0)
                    if 0 <= entry_channel <= 6:
                        mac_data_points.append({
                            'timestamp': entry.get('timestamp'),
                            'current': float(entry.get('parameter', 0)),
                            'channel': entry_channel,
                            'unit': entry.get('unit', 'A')
                        })
            
            # 按時間排序
            mac_data_points.sort(key=lambda x: x.get('timestamp', ''))
            
            logging.info(f"MAC ID {mac_id} 的電流數據點數量: {len(mac_data_points)}")
            
            return jsonify({
                'success': True,
                'mac_id': mac_id,
                'data': mac_data_points,  # 返回時間序列數據點
                'data_count': len(mac_data_points),
                'data_source': data_source,
                'message': f'MAC ID {mac_id} 的電流數據 (來源: {data_source}，共 {len(mac_data_points)} 個數據點)'
            })
        else:
            # 如果沒有指定 MAC ID，返回所有 MAC ID 的摘要
            mac_summary = {}
            for entry in data:
                entry_mac_id = entry.get('mac_id', 'N/A')
                if entry_mac_id not in ['N/A', '', None]:
                    if entry_mac_id not in mac_summary:
                        mac_summary[entry_mac_id] = {
                            'mac_id': entry_mac_id,
                            'data_count': 0,
                            'latest_timestamp': None
                        }
                    mac_summary[entry_mac_id]['data_count'] += 1
                    mac_summary[entry_mac_id]['latest_timestamp'] = entry.get('timestamp')
            
            return jsonify({
                'success': True,
                'data': mac_summary,
                'total_mac_ids': len(mac_summary),
                'data_source': data_source,
                'message': f'找到 {len(mac_summary)} 個 MAC ID 的數據 (來源: {data_source})'
            })
        
    except Exception as e:
        logging.error(f'獲取MAC通道資訊時發生錯誤: {str(e)}')
        return jsonify({
            'success': False, 
            'message': f'獲取MAC通道資訊時發生錯誤: {str(e)}',
            'data': {}
        })

@app.route('/api/uart/mac-data/<mac_id>', methods=['GET'])
def get_mac_data_10min(mac_id):
    """API: 獲取特定MAC ID最近N分鐘的電流數據"""
    try:
        # 獲取時間範圍參數，預設為10分鐘
        minutes = request.args.get('minutes', 10, type=int)
        
        # 優先嘗試從 uart_reader 獲取數據
        data = []
        data_source = "直接讀取"
        
        if 'uart_reader' in globals() and uart_reader and hasattr(uart_reader, 'get_latest_data'):
            try:
                data = uart_reader.get_latest_data()
                if data:
                    data_source = "即時數據"
            except Exception as e:
                logging.warning(f"從uart_reader獲取數據失敗: {e}")
        
        # 如果沒有即時數據，嘗試從文件獲取
        if not data:
            logging.info("嘗試從History文件獲取電流數據")
            data_info = get_uart_data_from_files()
            if data_info.get('success'):
                # 從分組的通道數據中提取所有原始數據
                data = []
                for channel_data in data_info.get('data', []):
                    for data_point in channel_data.get('data', []):
                        data.append({
                            'mac_id': data_point.get('mac_id', channel_data.get('mac_id', 'N/A')),
                            'channel': channel_data.get('channel', 0),
                            'timestamp': data_point.get('timestamp'),
                            'parameter': data_point.get('parameter'),
                            'unit': channel_data.get('unit', 'A')
                        })
                data_source = "歷史文件"
                logging.info(f"從歷史文件載入了 {len(data)} 筆原始數據")
            else:
                logging.warning(f"從文件獲取數據失敗: {data_info.get('error', '未知錯誤')}")

        if not data:
            return jsonify({
                'success': False,
                'data': [],
                'message': '暫無UART數據，請先啟動UART讀取或檢查數據文件'
            })
        
        # 計算時間範圍
        time_limit = datetime.now() - timedelta(minutes=minutes)
        
        # 過濾指定MAC ID和時間範圍內的數據
        filtered_data = []
        for entry in data:
            if entry.get('mac_id') != mac_id:
                continue
                
            # 只包含電流數據 (單位為 'A')，排除頻道7電池電壓
            if entry.get('unit') != 'A':
                continue
                
            entry_channel = entry.get('channel', 0)
            if not (0 <= entry_channel <= 6):
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
                # 如果沒有時間戳，假設是最新數據（保留）
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
        
        logging.info(f'獲取MAC ID {mac_id} 最近 {minutes} 分鐘數據: {len(filtered_data)} 筆 (來源: {data_source})')
        
        return jsonify({
            'success': True,
            'data': filtered_data,
            'mac_id': mac_id,
            'time_range_minutes': minutes,
            'total_data_points': len(filtered_data),
            'data_source': data_source,
            'message': f'MAC ID {mac_id} 最近 {minutes} 分鐘有 {len(filtered_data)} 筆電流數據 (來源: {data_source})'
        })
        
    except Exception as e:
        logging.exception(f'獲取MAC ID {mac_id} 數據時發生錯誤: {str(e)}')
        return jsonify({
            'success': False,
            'data': [],
            'message': f'獲取數據時發生錯誤: {str(e)}'
        })

# ====== 協定相關API ======

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
        # 獲取目前啟用的協定
        active_protocol = config_manager.get_active_protocol()
        
        # 檢查協定管理器中的活動協定
        running_protocol = getattr(protocol_manager, 'active', None) if 'protocol_manager' in globals() else None
        
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
            if 'protocol_manager' in globals():
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

# ====== UART相關API ======

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
        return jsonify({'success': True, 'message': 'UART讀取已停止'})
    except Exception as e:
        logging.exception(f'停止UART時發生錯誤: {str(e)}')
        return jsonify({'success': False, 'message': f'停止UART時發生錯誤: {str(e)}'})

@app.route('/api/uart/clear', methods=['POST'])
def clear_uart_data():
    """API: 清除UART資料"""
    try:
        uart_reader.clear_data()
        return jsonify({'success': True, 'message': 'UART資料已清除'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'清除UART資料時發生錯誤: {str(e)}'})

@app.route('/api/uart/diagnostic', methods=['POST'])
def uart_diagnostic():
    """API: 執行UART診斷"""
    try:
        import subprocess
        
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

# ====== FTP相關API ======

@app.route('/api/ftp/upload', methods=['POST'])
def ftp_manual_upload():
    logging.info(f'API: 手動觸發FTP上傳, remote_addr={request.remote_addr}')
    try:
        if 'protocol_manager' in globals() and protocol_manager.active == 'FTP':
            ftp_receiver = protocol_manager.protocols['FTP']
            # 觴發立即上傳
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
        if 'protocol_manager' in globals() and protocol_manager.active == 'FTP':
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
        from io import BytesIO
        
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

# ====== 系統狀態API ======

@app.route('/api/system/status')
def system_status():
    """API: 獲取系統狀態，包括網路和離線模式"""
    try:
        # 使用網路檢查器獲取狀態
        network_status = network_checker.get_network_status()
        offline_mode = config_manager.get('offline_mode', False)
        
        return jsonify({
            'success': True,
            'network_status': network_status,
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

# ====== WiFi相關API ======

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

# ====== 主機連接API ======

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

# ====== 模式管理API ======

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
                        if 'protocol_manager' in globals():
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

# ====== 資料庫相關 API ======

@app.route('/api/database/factory-areas')
def get_database_factory_areas():
    """取得資料庫中的廠區列表"""
    if not DATABASE_AVAILABLE or not db_manager:
        return jsonify({
            'success': False,
            'message': '資料庫功能未啟用',
            'data': []
        })
    
    try:
        areas = db_manager.get_factory_areas()
        return jsonify({
            'success': True,
            'data': areas,
            'count': len(areas)
        })
    except Exception as e:
        logging.error(f"取得廠區列表失敗: {e}")
        return jsonify({
            'success': False,
            'message': f'取得廠區列表失敗: {str(e)}',
            'data': []
        })

@app.route('/api/database/floor-levels')
def get_database_floor_levels():
    """取得資料庫中的樓層列表"""
    if not DATABASE_AVAILABLE or not db_manager:
        return jsonify({
            'success': False,
            'message': '資料庫功能未啟用',
            'data': []
        })
    
    try:
        factory_area = request.args.get('factory_area')
        floors = db_manager.get_floor_levels(factory_area)
        return jsonify({
            'success': True,
            'data': floors,
            'count': len(floors),
            'filter': {'factory_area': factory_area}
        })
    except Exception as e:
        logging.error(f"取得樓層列表失敗: {e}")
        return jsonify({
            'success': False,
            'message': f'取得樓層列表失敗: {str(e)}',
            'data': []
        })

@app.route('/api/database/mac-ids')
def get_database_mac_ids():
    """取得資料庫中的 MAC ID 列表"""
    if not DATABASE_AVAILABLE or not db_manager:
        return jsonify({
            'success': False,
            'message': '資料庫功能未啟用',
            'data': []
        })
    
    try:
        factory_area = request.args.get('factory_area')
        floor_level = request.args.get('floor_level')
        mac_ids = db_manager.get_mac_ids(factory_area, floor_level)
        return jsonify({
            'success': True,
            'data': mac_ids,
            'count': len(mac_ids),
            'filter': {'factory_area': factory_area, 'floor_level': floor_level}
        })
    except Exception as e:
        logging.error(f"取得 MAC ID 列表失敗: {e}")
        return jsonify({
            'success': False,
            'message': f'取得 MAC ID 列表失敗: {str(e)}',
            'data': []
        })

@app.route('/api/database/device-models')
def get_database_device_models():
    """取得資料庫中的設備型號列表"""
    if not DATABASE_AVAILABLE or not db_manager:
        return jsonify({
            'success': False,
            'message': '資料庫功能未啟用',
            'data': []
        })
    
    try:
        factory_area = request.args.get('factory_area')
        floor_level = request.args.get('floor_level')
        mac_id = request.args.get('mac_id')
        models = db_manager.get_device_models(factory_area, floor_level, mac_id)
        return jsonify({
            'success': True,
            'data': models,
            'count': len(models),
            'filter': {
                'factory_area': factory_area, 
                'floor_level': floor_level,
                'mac_id': mac_id
            }
        })
    except Exception as e:
        logging.error(f"取得設備型號列表失敗: {e}")
        return jsonify({
            'success': False,
            'message': f'取得設備型號列表失敗: {str(e)}',
            'data': []
        })

@app.route('/api/database/chart-data')
def get_database_chart_data():
    """取得資料庫中的圖表資料"""
    if not DATABASE_AVAILABLE or not db_manager:
        return jsonify({
            'success': False,
            'message': '資料庫功能未啟用',
            'data': []
        })
    
    try:
        # 解析請求參數
        factory_area = request.args.get('factory_area')
        floor_level = request.args.get('floor_level')
        mac_id = request.args.get('mac_id')
        device_model = request.args.get('device_model')
        data_type = request.args.get('data_type', 'temperature')  # 預設為溫度
        limit = int(request.args.get('limit', 1000))
        
        # 時間範圍
        start_time = None
        end_time = None
        
        start_time_str = request.args.get('start_time')
        end_time_str = request.args.get('end_time')
        
        if start_time_str:
            try:
                start_time = datetime.fromisoformat(start_time_str.replace('Z', '+00:00'))
            except ValueError:
                start_time = datetime.strptime(start_time_str, '%Y-%m-%d %H:%M:%S')
        
        if end_time_str:
            try:
                end_time = datetime.fromisoformat(end_time_str.replace('Z', '+00:00'))
            except ValueError:
                end_time = datetime.strptime(end_time_str, '%Y-%m-%d %H:%M:%S')
        
        # 如果沒有指定時間範圍，預設取最近24小時的資料
        if not start_time:
            start_time = datetime.now() - timedelta(hours=24)
        
        # 取得圖表資料
        chart_data = db_manager.get_chart_data(
            factory_area=factory_area,
            floor_level=floor_level,
            mac_id=mac_id,
            device_model=device_model,
            start_time=start_time,
            end_time=end_time,
            data_type=data_type,
            limit=limit
        )
        
        # 格式化資料供前端使用
        formatted_data = []
        for item in chart_data:
            formatted_data.append({
                'x': item['timestamp'],
                'y': item['value'],
                'mac_id': item['mac_id'],
                'device_model': item['device_model'],
                'factory_area': item['factory_area'],
                'floor_level': item['floor_level']
            })
        
        return jsonify({
            'success': True,
            'data': formatted_data,
            'count': len(formatted_data),
            'data_type': data_type,
            'filter': {
                'factory_area': factory_area,
                'floor_level': floor_level,
                'mac_id': mac_id,
                'device_model': device_model,
                'start_time': start_time.isoformat() if start_time else None,
                'end_time': end_time.isoformat() if end_time else None,
                'limit': limit
            }
        })
        
    except Exception as e:
        logging.error(f"取得圖表資料失敗: {e}")
        return jsonify({
            'success': False,
            'message': f'取得圖表資料失敗: {str(e)}',
            'data': []
        })

@app.route('/api/database/statistics')
def get_database_statistics():
    """取得資料庫統計資訊"""
    if not DATABASE_AVAILABLE or not db_manager:
        return jsonify({
            'success': False,
            'message': '資料庫功能未啟用',
            'data': {}
        })
    
    try:
        stats = db_manager.get_statistics()
        return jsonify({
            'success': True,
            'data': stats
        })
    except Exception as e:
        logging.error(f"取得資料庫統計資訊失敗: {e}")
        return jsonify({
            'success': False,
            'message': f'取得資料庫統計資訊失敗: {str(e)}',
            'data': {}
        })

@app.route('/api/database/latest-data')
def get_database_latest_data():
    """取得最新的資料"""
    if not DATABASE_AVAILABLE or not db_manager:
        return jsonify({
            'success': False,
            'message': '資料庫功能未啟用',
            'data': []
        })
    
    try:
        mac_id = request.args.get('mac_id')
        limit = int(request.args.get('limit', 10))
        
        latest_data = db_manager.get_latest_data(mac_id, limit)
        return jsonify({
            'success': True,
            'data': latest_data,
            'count': len(latest_data),
            'filter': {'mac_id': mac_id, 'limit': limit}
        })
    except Exception as e:
        logging.error(f"取得最新資料失敗: {e}")
        return jsonify({
            'success': False,
            'message': f'取得最新資料失敗: {str(e)}',
            'data': []
        })

@app.route('/api/database/register-device', methods=['POST'])
def register_device():
    """註冊設備資訊"""
    if not DATABASE_AVAILABLE or not db_manager:
        return jsonify({
            'success': False,
            'message': '資料庫功能未啟用'
        })
    
    try:
        device_info = request.get_json()
        if not device_info:
            return jsonify({
                'success': False,
                'message': '請提供設備資訊'
            })
        
        success = db_manager.register_device(device_info)
        if success:
            return jsonify({
                'success': True,
                'message': '設備註冊成功'
            })
        else:
            return jsonify({
                'success': False,
                'message': '設備註冊失敗'
            })
    except Exception as e:
        logging.error(f"註冊設備失敗: {e}")
        return jsonify({
            'success': False,
            'message': f'註冊設備失敗: {str(e)}'
        })

@app.route('/api/database/device-info')
def get_database_device_info():
    """取得設備資訊"""
    if not DATABASE_AVAILABLE or not db_manager:
        return jsonify({
            'success': False,
            'message': '資料庫功能未啟用',
            'data': []
        })
    
    try:
        mac_id = request.args.get('mac_id')
        device_info = db_manager.get_device_info(mac_id)
        return jsonify({
            'success': True,
            'data': device_info,
            'count': len(device_info),
            'filter': {'mac_id': mac_id}
        })
    except Exception as e:
        logging.error(f"取得設備資訊失敗: {e}")
        return jsonify({
            'success': False,
            'message': f'取得設備資訊失敗: {str(e)}',
            'data': []
        })

# ====== 錯誤處理 ======

@app.errorhandler(404)
def not_found_error(error):
    """處理404錯誤"""
    return jsonify({
        'success': False,
        'error': 'Not Found',
        'message': '請求的資源不存在'
    }), 404

@app.errorhandler(500)
def internal_error(error):
    """處理500錯誤"""
    logging.error(f"內部伺服器錯誤: {error}")
    return jsonify({
        'success': False,
        'error': 'Internal Server Error',
        'message': '內部伺服器錯誤'
    }), 500

def initialize_raspberry_pi_connection():
    """初始化樹莓派連接"""
    try:
        # 嘗試自動連接樹莓派
        if RASPBERRY_PI_CONFIG.get('auto_discover', True):
            try:
                pi_connection = auto_connect_raspberry_pi()
                if pi_connection['connected']:
                    logging.info(f"樹莓派連接成功: {RASPBERRY_PI_CONFIG['host']}")
                else:
                    logging.warning(f"樹莓派連接失敗: {pi_connection.get('message', '未知錯誤')}")
            except Exception as e:
                logging.error(f"樹莓派自動連接時發生錯誤: {e}")
        else:
            # 只測試當前配置的連接
            pi_status = test_raspberry_pi_connection()
            if pi_status['connected']:
                logging.info(f"樹莓派連接正常: {RASPBERRY_PI_CONFIG['host']}")
            else:
                logging.warning(f"樹莓派連接異常: {pi_status.get('message', '未知錯誤')}")
    except Exception as e:
        logging.error(f"初始化樹莓派連接時發生錯誤: {e}")

if __name__ == '__main__':
    try:
        print("啟動 Dashboard API 服務...")
        print("支援的路由:")
        print("  - Dashboard 主頁: http://localhost:5001/dashboard")
        print("  - 設備設定: http://localhost:5001/db-setting")
        print("  - API 健康檢查: http://localhost:5001/api/health")
        print("  - API 狀態: http://localhost:5001/api/status")
        
        # 初始化樹莓派連接
        initialize_raspberry_pi_connection()
        
        # 啟動 Flask 應用程式 (使用不同的端口避免衝突)
        app.run(debug=True, host='0.0.0.0', port=5001)
        
    except Exception as e:
        print(f"啟動 Dashboard API 服務時發生錯誤: {e}")
        print("請檢查:")
        print("1. 端口 5001 是否被其他程式佔用")
        print("2. 相依套件是否已正確安裝")
