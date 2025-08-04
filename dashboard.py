"""
Dashboard API 服務
獨立的 Dashboard 和設備設定管理 API 服務
"""

from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, make_response
from config_manager import ConfigManager
from uart_integrated import uart_reader
from device_settings import DeviceSettingsManager
from multi_device_settings import MultiDeviceSettingsManager
import os
import json
import logging
import platform
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

# 初始化管理器
config_manager = ConfigManager()
device_settings_manager = DeviceSettingsManager()
multi_device_settings_manager = MultiDeviceSettingsManager()

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
    
    # 提供基本的系統監控資訊
    system_info = get_detailed_system_info()
    
    # 應用程式統計
    try:
        app_stats = {
            'uart_running': uart_reader.is_running if uart_reader else False,
            'uart_data_count': uart_reader.get_data_count() if uart_reader else 0,
            'active_protocol': config_manager.get_active_protocol(),
            'offline_mode': config_manager.get('offline_mode', False),
            'supported_protocols': config_manager.get_supported_protocols(),
        }
    except Exception as app_stats_error:
        logging.error(f"獲取應用程式統計時發生錯誤: {app_stats_error}")
        app_stats = {
            'uart_running': False,
            'uart_data_count': 0,
            'active_protocol': 'N/A',
            'offline_mode': True,
            'supported_protocols': [],
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
        system_stats = get_system_stats()
        
        # 應用程式統計
        try:
            app_stats = {
                'uart_running': uart_reader.is_running if uart_reader else False,
                'uart_data_count': uart_reader.get_data_count() if uart_reader else 0,
                'active_protocol': config_manager.get_active_protocol(),
                'offline_mode': config_manager.get('offline_mode', False),
                'current_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            }
        except Exception as app_error:
            logging.error(f"獲取應用程式統計時發生錯誤: {app_error}")
            app_stats = {
                'uart_running': False,
                'uart_data_count': 0,
                'active_protocol': 'N/A',
                'offline_mode': True,
                'current_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
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
        limit = request.args.get('limit', 100000, type=int)  # 預設最近100000筆數據，如需更多可調整參數
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
        raw_data = safe_get_uart_data()
        
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
        raw_data = safe_get_uart_data()
        
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

if __name__ == '__main__':
    try:
        print("啟動 Dashboard API 服務...")
        print("支援的路由:")
        print("  - Dashboard 主頁: http://localhost:5001/dashboard")
        print("  - 設備設定: http://localhost:5001/db-setting")
        print("  - API 健康檢查: http://localhost:5001/api/health")
        print("  - API 狀態: http://localhost:5001/api/status")
        
        # 啟動 Flask 應用程式 (使用不同的端口避免衝突)
        app.run(debug=True, host='0.0.0.0', port=5001)
        
    except Exception as e:
        print(f"啟動 Dashboard API 服務時發生錯誤: {e}")
        print("請檢查:")
        print("1. 端口 5001 是否被其他程式佔用")
        print("2. 相依套件是否已正確安裝")
