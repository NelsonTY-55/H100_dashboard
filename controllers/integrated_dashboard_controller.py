# controllers/integrated_dashboard_controller.py
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
import logging
import os
from datetime import datetime, timedelta

# 創建 Blueprint
integrated_dashboard_bp = Blueprint('integrated_dashboard', __name__)


@integrated_dashboard_bp.route('/dashboard')
def flask_dashboard():
    """Flask Dashboard 主頁面"""
    logging.info(f'訪問Flask Dashboard, remote_addr={request.remote_addr}')
    
    from device_settings import device_settings_manager
    from config_manager import config_manager
    from uart_integrated import uart_reader
    
    # 檢查設備設定是否完成
    if not device_settings_manager.is_configured():
        logging.info("設備尚未設定，重定向到設定頁面")
        flash('請先完成設備設定', 'warning')
        return redirect(url_for('integrated_device.db_setting', redirect='true'))
    
    # 檢查是否有安裝 flask-monitoringdashboard
    try:
        import flask_monitoringdashboard
        DASHBOARD_AVAILABLE = True
    except ImportError:
        DASHBOARD_AVAILABLE = False
    
    if DASHBOARD_AVAILABLE:
        try:
            # 嘗試重定向到 Flask MonitoringDashboard
            return redirect('/dashboard/')
        except Exception as redirect_error:
            logging.warning(f"重定向到 MonitoringDashboard 失敗: {redirect_error}")
    
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
        # 需要從外部定義或導入 current_mode
        current_mode = {'mode': 'idle'}  # 預設值
        
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


@integrated_dashboard_bp.route('/api/dashboard/stats')
def dashboard_stats():
    """API: 獲取 Dashboard 統計資料"""
    try:
        # 系統資源資訊
        try:
            import psutil
            try:
                cpu_percent = psutil.cpu_percent(interval=0.1)
            except:
                cpu_percent = 0
                
            try:
                memory_info = psutil.virtual_memory()._asdict()
            except:
                memory_info = {'percent': 0, 'total': 0, 'available': 0}
                
            try:
                if os.name == 'nt':
                    disk_info = psutil.disk_usage('C:\\')._asdict()
                else:
                    disk_info = psutil.disk_usage('/')._asdict()
            except:
                disk_info = {'percent': 0, 'total': 0, 'free': 0}
                
            try:
                network_info = psutil.net_io_counters()._asdict() if psutil.net_io_counters() else {}
            except:
                network_info = {}
                
        except ImportError:
            cpu_percent = 0
            memory_info = {'percent': 0, 'total': 0, 'available': 0}
            disk_info = {'percent': 0, 'total': 0, 'free': 0}
            network_info = {}
        
        # 應用程式統計
        from uart_integrated import uart_reader
        from config_manager import config_manager
        
        # 需要從外部定義或導入 offline_mode_manager
        try:
            from multi_protocol_manager import offline_mode_manager
            current_mode = offline_mode_manager.get_current_mode()
        except:
            current_mode = 'idle'
        
        app_stats = {
            'uart_running': uart_reader.is_running,
            'uart_data_count': uart_reader.get_data_count(),
            'active_protocol': config_manager.get_active_protocol(),
            'offline_mode': config_manager.get('offline_mode', False),
            'supported_protocols': config_manager.get_supported_protocols(),
            'current_mode': current_mode
        }
        
        return jsonify({
            'success': True,
            'system': {
                'cpu_percent': cpu_percent,
                'memory': memory_info,
                'disk': disk_info,
                'network': network_info
            },
            'app': app_stats
        })
        
    except Exception as e:
        logging.error(f"獲取 Dashboard 統計資料失敗: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@integrated_dashboard_bp.route('/api/dashboard/device-settings')
def dashboard_device_settings():
    """API: 獲取設備設定資料"""
    try:
        from device_settings import device_settings_manager
        settings = device_settings_manager.load_settings()
        
        return jsonify({
            'success': True,
            'settings': settings
        })
    except Exception as e:
        logging.error(f"獲取設備設定失敗: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@integrated_dashboard_bp.route('/api/dashboard/chart-data')
def dashboard_chart_data():
    """API: 獲取圖表資料"""
    try:
        from uart_integrated import uart_reader
        
        # 獲取時間範圍參數
        hours = request.args.get('hours', 24, type=int)  # 預設24小時
        mac_id = request.args.get('mac_id', '')  # MAC ID過濾
        parameter = request.args.get('parameter', '')  # 參數過濾
        
        # 計算時間範圍
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=hours)
        
        # 獲取UART資料
        uart_data = uart_reader.get_latest_data()
        
        # 過濾資料
        filtered_data = []
        if uart_data:
            for item in uart_data:
                if isinstance(item, dict):
                    # 時間過濾
                    if 'timestamp' in item:
                        try:
                            item_time = datetime.fromisoformat(item['timestamp'])
                            if item_time < start_time:
                                continue
                        except:
                            pass  # 如果時間解析失敗，包含這個項目
                    
                    # MAC ID過濾
                    if mac_id and item.get('mac_id', '') != mac_id:
                        continue
                        
                    # 參數過濾
                    if parameter and item.get('parameter', '') != parameter:
                        continue
                        
                    filtered_data.append(item)
        
        # 準備圖表資料
        chart_data = {
            'labels': [],
            'datasets': []
        }
        
        # 按參數分組資料
        parameter_data = {}
        for item in filtered_data:
            param_key = f"{item.get('parameter', 'Unknown')} ({item.get('unit', '')})"
            if param_key not in parameter_data:
                parameter_data[param_key] = {
                    'data': [],
                    'label': param_key,
                    'borderColor': f'rgb({hash(param_key) % 255}, {(hash(param_key) * 2) % 255}, {(hash(param_key) * 3) % 255})',
                    'backgroundColor': f'rgba({hash(param_key) % 255}, {(hash(param_key) * 2) % 255}, {(hash(param_key) * 3) % 255}, 0.1)'
                }
            
            # 添加資料點
            parameter_data[param_key]['data'].append({
                'x': item.get('timestamp', ''),
                'y': item.get('value', 0)
            })
        
        # 轉換為Chart.js格式
        chart_data['datasets'] = list(parameter_data.values())
        
        return jsonify({
            'success': True,
            'chart_data': chart_data,
            'data_count': len(filtered_data),
            'time_range': {
                'start': start_time.isoformat(),
                'end': end_time.isoformat(),
                'hours': hours
            }
        })
        
    except Exception as e:
        logging.error(f"獲取圖表資料失敗: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500