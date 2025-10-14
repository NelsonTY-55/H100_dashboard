"""
Dashboard 控制器 - 重構版本
處理儀表板相關的路由和邏輯，使用新的 MVC 架構
"""

from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
import logging
import os
from datetime import datetime
from typing import Optional

# 創建 Blueprint
dashboard_bp = Blueprint('dashboard', __name__)

# 全域變數，將在初始化時設置
dashboard_model = None
chart_model = None
db_model = None
uart_model = None
device_areas_model = None


def init_controller(db_manager=None, uart_reader=None):
    """初始化控制器，設置模型實例"""
    global dashboard_model, chart_model, db_model, uart_model, device_areas_model
    
    from models.dashboard_model import (
        DashboardModel, ChartDataModel, DatabaseModel, 
        DeviceAreasModel, UartDataModel
    )
    
    dashboard_model = DashboardModel()
    chart_model = ChartDataModel()
    db_model = DatabaseModel(db_manager)
    uart_model = UartDataModel(uart_reader)
    device_areas_model = DeviceAreasModel()


# ====== 頁面路由 ======

@dashboard_bp.route('/dashboard')
def flask_dashboard():
    """Flask Dashboard 主頁面"""
    logging.info(f'訪問Flask Dashboard, remote_addr={request.remote_addr}')
    
    try:
        # 檢查設備設定是否完成
        from device_settings import device_settings_manager
        if not device_settings_manager.is_configured():
            logging.info("設備尚未設定，重定向到設定頁面")
            flash('請先完成設備設定', 'warning')
            return redirect(url_for('device.db_setting', redirect='true'))
        
        # 獲取系統資訊
        system_info = dashboard_model.get_system_info()
        
        # 獲取應用程式統計
        from uart_integrated import uart_reader
        app_stats = dashboard_model.get_application_stats(uart_reader)
        
        # 獲取設備設定資訊
        device_settings = {
            'device_name': device_settings_manager.settings.get('device_name', '未設定設備'),
            'device_location': device_settings_manager.settings.get('device_location', ''),
            'device_model': device_settings_manager.settings.get('device_model', ''),
            'device_serial': device_settings_manager.settings.get('device_serial', ''),
            'device_description': device_settings_manager.settings.get('device_description', ''),
            'created_at': device_settings_manager.settings.get('created_at'),
            'updated_at': device_settings_manager.settings.get('updated_at')
        }
        
        return render_template('dashboard.html',
                             system_info=system_info,
                             app_stats=app_stats,
                             device_settings=device_settings,
                             raspberry_pi_config={'host': '本地主機', 'port': 5001},
                             pi_status={'connected': False})
        
    except Exception as e:
        logging.error(f"載入 Dashboard 時發生錯誤: {e}")
        return render_template('error.html', error=str(e)), 500


@dashboard_bp.route('/data-analysis')
def data_analysis():
    """資料分析頁面"""
    logging.info(f'訪問資料分析頁面, remote_addr={request.remote_addr}')
    
    # 檢查資料庫是否可用
    if not db_model or not db_model.database_available:
        flash('資料庫功能未啟用，請檢查系統配置', 'error')
        return redirect(url_for('dashboard.flask_dashboard'))
    
    return render_template('data_analysis.html')


@dashboard_bp.route('/11')
def dashboard_11():
    """儀表板總覽頁面 (11.html)"""
    logging.info(f'訪問儀表板總覽頁面 11.html, remote_addr={request.remote_addr}')
    return render_template('11.html')


# ====== API 路由 ======

# ===== 健康檢查和狀態 =====

@dashboard_bp.route('/api/health')
def health_check():
    """健康檢查 API"""
    return jsonify(dashboard_model.get_health_status())


@dashboard_bp.route('/api/status')
def status():
    """服務狀態 API"""
    from uart_integrated import uart_reader
    from device_settings import device_settings_manager
    return jsonify(dashboard_model.get_service_status(uart_reader, device_settings_manager))


# ===== Dashboard 相關 API =====

@dashboard_bp.route('/api/dashboard/stats')
def dashboard_stats():
    """API: 獲取 Dashboard 統計資料"""
    try:
        from uart_integrated import uart_reader
        from device_settings import device_settings_manager
        
        # 獲取系統統計
        system_stats = dashboard_model.get_system_info()
        
        # 獲取應用程式統計
        app_stats = dashboard_model.get_application_stats(uart_reader)
        
        # 獲取設備設定
        if device_settings_manager.is_configured():
            device_settings = {
                'device_name': device_settings_manager.settings.get('device_name', '未設定設備'),
                'device_location': device_settings_manager.settings.get('device_location', ''),
                'device_model': device_settings_manager.settings.get('device_model', ''),
                'device_serial': device_settings_manager.settings.get('device_serial', ''),
                'device_description': device_settings_manager.settings.get('device_description', '')
            }
        else:
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
            'source': '本地',
            'connection_status': '本地模式'
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
                'network_recv': 0
            },
            'application': {
                'uptime': datetime.now().isoformat(),
                'uart_connection': False,
                'total_devices': 0,
                'active_connections': 0,
                'data_points_today': 0
            },
            'device_settings': {
                'device_name': '錯誤',
                'device_location': '',
                'device_model': '',
                'device_serial': '',
                'device_description': ''
            }
        })


@dashboard_bp.route('/api/dashboard/device-settings')
def dashboard_device_settings():
    """API: 獲取設備設定資料"""
    try:
        from device_settings import device_settings_manager
        from multi_device_settings import multi_device_settings_manager
        
        # 獲取單設備設定
        device_settings = device_settings_manager.load_settings()
        
        # 獲取多設備設定
        multi_device_settings = multi_device_settings_manager.get_all_device_settings()
        
        return jsonify({
            'success': True,
            'device_settings': device_settings,
            'multi_device_settings': multi_device_settings,
            'is_configured': device_settings_manager.is_configured(),
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logging.error(f"獲取設備設定資料時發生錯誤: {e}")
        return jsonify({
            'success': False,
            'message': f'獲取設備設定資料失敗: {str(e)}',
            'device_settings': {},
            'multi_device_settings': {}
        })


@dashboard_bp.route('/api/dashboard/chart-data')
def dashboard_chart_data():
    """API: 獲取圖表數據 (本地模式)"""
    try:
        mac_id = request.args.get('mac_id')
        limit = int(request.args.get('limit', 1000))
        
        # 使用圖表模型獲取資料
        result = chart_model.get_local_chart_data(mac_id=mac_id, limit=limit)
        return jsonify(result)
        
    except Exception as e:
        logging.error(f"獲取圖表數據時發生錯誤: {e}")
        return jsonify({
            'success': False,
            'message': f'獲取圖表數據失敗: {str(e)}',
            'data': [],
            'total_channels': 0,
            'source': '錯誤',
            'raspberry_pi_ip': '本地主機',
            'timestamp': datetime.now().isoformat()
        })


@dashboard_bp.route('/api/dashboard/devices')
def dashboard_devices():
    """API: 獲取所有設備列表"""
    try:
        from multi_device_settings import multi_device_settings_manager
        
        # 獲取所有設備
        devices = multi_device_settings_manager.get_all_device_settings()
        
        # 轉換為列表格式
        device_list = []
        for device_id, settings in devices.items():
            device_info = {
                'device_id': device_id,
                'device_name': settings.get('device_name', f'設備 {device_id}'),
                'factory_area': settings.get('factory_area', ''),
                'floor_level': settings.get('floor_level', ''),
                'device_model': settings.get('device_model', ''),
                'mac_address': settings.get('mac_address', ''),
                'ip_address': settings.get('ip_address', ''),
                'created_at': settings.get('created_at', ''),
                'updated_at': settings.get('updated_at', '')
            }
            device_list.append(device_info)
        
        return jsonify({
            'success': True,
            'devices': device_list,
            'count': len(device_list),
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logging.error(f"獲取設備列表時發生錯誤: {e}")
        return jsonify({
            'success': False,
            'message': f'獲取設備列表失敗: {str(e)}',
            'devices': [],
            'count': 0
        })


@dashboard_bp.route('/api/dashboard/areas')
def api_dashboard_areas():
    """API: 獲取所有廠區、位置、設備型號統計資料"""
    result = device_areas_model.get_areas_statistics()
    return jsonify(result)


@dashboard_bp.route('/api/dashboard/overview')
def dashboard_overview_api():
    """API: 儀表板總覽頁面專用 - 提供綜合統計資訊"""
    try:
        from uart_integrated import uart_reader
        from device_settings import device_settings_manager
        from multi_device_settings import multi_device_settings_manager
        
        # 系統資訊
        system_info = dashboard_model.get_system_info()
        
        # 應用程式統計
        app_stats = dashboard_model.get_application_stats(uart_reader)
        
        # 設備統計
        all_devices = multi_device_settings_manager.get_all_device_settings()
        device_count = len(all_devices)
        
        # UART 統計
        uart_stats = uart_model.get_status() if uart_model else {'status': 'not_available'}
        
        # 區域統計
        areas_stats = device_areas_model.get_areas_statistics()
        
        return jsonify({
            'success': True,
            'overview': {
                'system': {
                    'cpu_usage': system_info.get('cpu_percent', 0),
                    'memory_usage': system_info.get('memory_percent', 0),
                    'disk_usage': system_info.get('disk_percent', 0)
                },
                'devices': {
                    'total_count': device_count,
                    'active_count': 1 if device_settings_manager.is_configured() else 0,
                    'areas_count': len(areas_stats.get('areas', [])),
                    'locations_count': len(areas_stats.get('locations', []))
                },
                'uart': {
                    'status': uart_stats.get('status', 'unknown'),
                    'data_count': uart_stats.get('data_count', 0)
                },
                'application': {
                    'uptime': app_stats.get('uptime'),
                    'version': '1.0.0',
                    'last_update': datetime.now().isoformat()
                }
            },
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logging.error(f"獲取總覽資訊時發生錯誤: {e}")
        return jsonify({
            'success': False,
            'message': f'獲取總覽資訊失敗: {str(e)}'
        })


# ===== UART 相關 API =====

@dashboard_bp.route('/api/uart/status')
def uart_status():
    """API: 獲取UART狀態"""
    if not uart_model:
        return jsonify({
            'success': False,
            'message': 'UART 模型未初始化',
            'status': 'not_available'
        })
    
    result = uart_model.get_status()
    return jsonify(result)


@dashboard_bp.route('/api/uart/mac-ids', methods=['GET'])
def get_uart_mac_ids():
    """API: 獲取UART接收到的MAC ID列表"""
    if not uart_model:
        return jsonify({
            'success': False,
            'message': 'UART 模型未初始化',
            'mac_ids': []
        })
    
    result = uart_model.get_mac_ids()
    return jsonify(result)


@dashboard_bp.route('/api/uart/mac-channels/', methods=['GET'])
@dashboard_bp.route('/api/uart/mac-channels/<mac_id>', methods=['GET'])
def get_uart_mac_channels(mac_id=None):
    """API: 獲取指定MAC ID的通道資訊，或所有MAC ID的通道統計"""
    if not uart_model:
        return jsonify({
            'success': False,
            'message': 'UART 模型未初始化',
            'data': {}
        })
    
    result = uart_model.get_mac_channels(mac_id)
    return jsonify(result)


@dashboard_bp.route('/api/uart/mac-data/<mac_id>', methods=['GET'])
def get_mac_data_10min(mac_id):
    """API: 獲取特定MAC ID最近N分鐘的電流數據"""
    if not uart_model:
        return jsonify({
            'success': False,
            'message': 'UART 模型未初始化',
            'data': []
        })
    
    try:
        minutes = int(request.args.get('minutes', 10))
        result = uart_model.get_mac_data_recent(mac_id, minutes)
        return jsonify(result)
    except ValueError:
        return jsonify({
            'success': False,
            'message': '無效的時間參數',
            'data': []
        })


# ===== 資料庫相關 API =====

@dashboard_bp.route('/api/database/chart-data')
def get_database_chart_data():
    """取得資料庫中的圖表資料"""
    if not db_model or not db_model.database_available:
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
        data_type = request.args.get('data_type', 'temperature')
        limit = int(request.args.get('limit', 1000))
        
        # 時間範圍
        start_time_str = request.args.get('start_time')
        end_time_str = request.args.get('end_time')
        
        start_time = None
        end_time = None
        
        if start_time_str:
            try:
                start_time = datetime.fromisoformat(start_time_str.replace('Z', '+00:00'))
            except ValueError:
                pass
        
        if end_time_str:
            try:
                end_time = datetime.fromisoformat(end_time_str.replace('Z', '+00:00'))
            except ValueError:
                pass
        
        # 獲取資料
        result = db_model.get_chart_data(
            factory_area=factory_area,
            floor_level=floor_level,
            mac_id=mac_id,
            device_model=device_model,
            data_type=data_type,
            limit=limit,
            start_time=start_time,
            end_time=end_time
        )
        
        return jsonify(result)
        
    except Exception as e:
        logging.error(f"取得資料庫圖表資料失敗: {e}")
        return jsonify({
            'success': False,
            'message': f'取得圖表資料失敗: {str(e)}',
            'data': []
        })


@dashboard_bp.route('/api/database/statistics')
def get_database_statistics():
    """取得資料庫統計資訊"""
    if not db_model or not db_model.database_available:
        return jsonify({
            'success': False,
            'message': '資料庫功能未啟用',
            'data': {}
        })
    
    result = db_model.get_statistics()
    return jsonify(result)


@dashboard_bp.route('/api/database/latest-data')
def get_database_latest_data():
    """取得最新的資料"""
    if not db_model or not db_model.database_available:
        return jsonify({
            'success': False,
            'message': '資料庫功能未啟用',
            'data': []
        })
    
    try:
        limit = int(request.args.get('limit', 100))
        result = db_model.get_latest_data(limit=limit)
        return jsonify(result)
    except ValueError:
        return jsonify({
            'success': False,
            'message': '無效的 limit 參數',
            'data': []
        })


@dashboard_bp.route('/api/database/latest-auto')
def get_database_latest_auto():
    """自動載入最新資料 (輕量級)"""
    if not db_model or not db_model.database_available:
        return jsonify({
            'success': False,
            'message': '資料庫功能未啟用',
            'data': []
        })
    
    # 輕量級版本，只取少量最新資料
    result = db_model.get_latest_data(limit=10)
    return jsonify(result)


@dashboard_bp.route('/api/database/factory-areas')
def get_database_factory_areas():
    """取得資料庫中的廠區列表"""
    if not db_model or not db_model.database_available:
        return jsonify({
            'success': False,
            'message': '資料庫功能未啟用',
            'data': []
        })
    
    result = db_model.get_factory_areas()
    return jsonify(result)


@dashboard_bp.route('/api/database/register-device', methods=['POST'])
def register_device():
    """註冊設備資訊"""
    if not db_model or not db_model.database_available:
        return jsonify({
            'success': False,
            'message': '資料庫功能未啟用'
        })
    
    try:
        device_data = request.get_json()
        if not device_data:
            return jsonify({
                'success': False,
                'message': '無效的設備資料'
            })
        
        result = db_model.register_device(device_data)
        return jsonify(result)
        
    except Exception as e:
        logging.error(f"註冊設備失敗: {e}")
        return jsonify({
            'success': False,
            'message': f'註冊設備失敗: {str(e)}'
        })


@dashboard_bp.route('/api/database/device-info')
def get_database_device_info():
    """取得設備資訊"""
    if not db_model or not db_model.database_available:
        return jsonify({
            'success': False,
            'message': '資料庫功能未啟用',
            'data': []
        })
    
    mac_id = request.args.get('mac_id')
    result = db_model.get_device_info(mac_id=mac_id)
    return jsonify(result)


# ===== 錯誤處理 =====

@dashboard_bp.errorhandler(404)
def not_found_error(error):
    """處理404錯誤"""
    return jsonify({
        'success': False,
        'error': 'Not Found',
        'message': '請求的資源不存在'
    }), 404


@dashboard_bp.errorhandler(500)
def internal_error(error):
    """處理500錯誤"""
    logging.error(f"內部伺服器錯誤: {error}")
    return jsonify({
        'success': False,
        'error': 'Internal Server Error',
        'message': '內部伺服器錯誤'
    }), 500