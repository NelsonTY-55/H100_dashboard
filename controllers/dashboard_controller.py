"""
Dashboard 控制器 - MVC 架構
處理儀表板頁面路由和資料視覺化
"""

from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
import logging
import os
from datetime import datetime, timedelta
import json

# 創建 Blueprint
dashboard_bp = Blueprint('dashboard', __name__)

# 全域變數，將在初始化時設置
config_manager = None
device_settings_manager = None
database_manager = None
uart_reader = None

def init_controller(config_mgr, device_settings_mgr, db_manager, uart_reader_instance):
    """初始化控制器"""
    global config_manager, device_settings_manager, database_manager, uart_reader
    config_manager = config_mgr
    device_settings_manager = device_settings_mgr
    database_manager = db_manager
    uart_reader = uart_reader_instance

@dashboard_bp.route('/')
def home():
    """主頁路由 - 重定向到 dashboard"""
    return redirect(url_for('dashboard.flask_dashboard'))

@dashboard_bp.route('/dashboard')
def flask_dashboard():
    """Flask Dashboard 主頁面"""
    logging.info(f'訪問Flask Dashboard, remote_addr={request.remote_addr}')
    
    try:
        # 檢查設備設定是否完成
        if not device_settings_manager.is_configured():
            logging.info("設備尚未設定，重定向到設定頁面")
            flash('請先完成設備設定', 'warning')
            return redirect(url_for('device.db_setting', redirect='true'))
        
        # 獲取系統資訊
        system_info = get_system_info()
        
        # 獲取應用程式統計
        app_stats = get_application_stats()
        
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

@dashboard_bp.route('/11')
def dashboard_11():
    """儀表板總覽頁面 (11.html)"""
    logging.info(f'訪問儀表板總覽頁面 11.html, remote_addr={request.remote_addr}')
    return render_template('11.html')

@dashboard_bp.route('/data-analysis')
def data_analysis():
    """資料分析頁面"""
    logging.info(f'訪問資料分析頁面, remote_addr={request.remote_addr}')
    
    # 檢查資料庫是否可用
    if not database_manager:
        flash('資料庫功能未啟用，請檢查系統配置', 'error')
        return redirect(url_for('dashboard.flask_dashboard'))
    
    return render_template('data_analysis.html')

# ====== API 路由 ======

@dashboard_bp.route('/api/dashboard/stats')
def api_dashboard_stats():
    """API: 獲取儀表板統計資料"""
    try:
        stats = {
            'system_info': get_system_info(),
            'app_stats': get_application_stats(),
            'uart_stats': get_uart_stats(),
            'database_stats': get_database_stats(),
            'timestamp': datetime.now().isoformat()
        }
        return jsonify({'success': True, 'data': stats})
    except Exception as e:
        logging.error(f"獲取儀表板統計資料時發生錯誤: {e}")
        return jsonify({'success': False, 'message': str(e)})

@dashboard_bp.route('/api/dashboard/chart-data')
def api_chart_data():
    """API: 獲取圖表資料"""
    try:
        chart_type = request.args.get('type', 'temperature')
        hours = int(request.args.get('hours', 24))
        
        if not database_manager:
            return jsonify({'success': False, 'message': '資料庫未啟用'})
        
        # 根據圖表類型獲取不同的資料
        if chart_type == 'temperature':
            data = get_temperature_chart_data(hours)
        elif chart_type == 'humidity':
            data = get_humidity_chart_data(hours)
        elif chart_type == 'sensor_data':
            data = get_sensor_chart_data(hours)
        else:
            return jsonify({'success': False, 'message': '不支援的圖表類型'})
        
        return jsonify({'success': True, 'data': data})
    except Exception as e:
        logging.error(f"獲取圖表資料時發生錯誤: {e}")
        return jsonify({'success': False, 'message': str(e)})

@dashboard_bp.route('/api/dashboard/uart-data')
def api_uart_data():
    """API: 獲取即時 UART 資料"""
    try:
        if not uart_reader:
            return jsonify({'success': False, 'message': 'UART 讀取器未啟用'})
        
        # 獲取最新的 UART 資料
        recent_data = get_recent_uart_data()
        
        return jsonify({
            'success': True,
            'data': recent_data,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        logging.error(f"獲取 UART 資料時發生錯誤: {e}")
        return jsonify({'success': False, 'message': str(e)})

# ====== 輔助函數 ======

def get_system_info():
    """獲取系統資訊"""
    try:
        import psutil
        import platform
        
        # CPU 資訊
        cpu_percent = psutil.cpu_percent(interval=1)
        cpu_count = psutil.cpu_count()
        
        # 記憶體資訊
        memory = psutil.virtual_memory()
        memory_percent = memory.percent
        memory_total = round(memory.total / (1024**3), 2)  # GB
        memory_used = round(memory.used / (1024**3), 2)  # GB
        
        # 磁碟資訊
        disk = psutil.disk_usage('/')
        disk_percent = round((disk.used / disk.total) * 100, 2)
        disk_total = round(disk.total / (1024**3), 2)  # GB
        disk_used = round(disk.used / (1024**3), 2)  # GB
        
        return {
            'platform': platform.system(),
            'platform_release': platform.release(),
            'platform_version': platform.version(),
            'architecture': platform.machine(),
            'hostname': platform.node(),
            'cpu_count': cpu_count,
            'cpu_percent': cpu_percent,
            'memory_total_gb': memory_total,
            'memory_used_gb': memory_used,
            'memory_percent': memory_percent,
            'disk_total_gb': disk_total,
            'disk_used_gb': disk_used,
            'disk_percent': disk_percent
        }
    except Exception as e:
        logging.error(f"獲取系統資訊時發生錯誤: {e}")
        return {
            'platform': '未知',
            'cpu_percent': 0,
            'memory_percent': 0,
            'disk_percent': 0
        }

def get_application_stats():
    """獲取應用程式統計"""
    try:
        stats = {
            'uptime': get_app_uptime(),
            'uart_status': get_uart_status(),
            'database_status': get_database_status(),
            'config_status': get_config_status()
        }
        return stats
    except Exception as e:
        logging.error(f"獲取應用程式統計時發生錯誤: {e}")
        return {}

def get_uart_stats():
    """獲取 UART 統計資料"""
    try:
        if not uart_reader:
            return {'status': 'disabled', 'message': 'UART 讀取器未啟用'}
        
        return {
            'status': 'active' if uart_reader.is_reading else 'inactive',
            'total_received': getattr(uart_reader, 'total_received', 0),
            'last_received': getattr(uart_reader, 'last_received_time', None),
            'port': getattr(uart_reader, 'port', 'unknown')
        }
    except Exception as e:
        logging.error(f"獲取 UART 統計時發生錯誤: {e}")
        return {'status': 'error', 'message': str(e)}

def get_database_stats():
    """獲取資料庫統計資料"""
    try:
        if not database_manager:
            return {'status': 'disabled', 'message': '資料庫未啟用'}
        
        # 統計各表的資料數量
        stats = {
            'status': 'active',
            'tables': {}
        }
        
        # 這裡可以加入更多資料庫統計邏輯
        return stats
    except Exception as e:
        logging.error(f"獲取資料庫統計時發生錯誤: {e}")
        return {'status': 'error', 'message': str(e)}

def get_temperature_chart_data(hours=24):
    """獲取溫度圖表資料"""
    try:
        if not database_manager:
            return {'labels': [], 'data': []}
        
        # 實作溫度資料查詢邏輯
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=hours)
        
        # 這裡應該查詢資料庫獲取溫度資料
        # 暫時返回空資料
        return {
            'labels': [],
            'data': [],
            'unit': '°C'
        }
    except Exception as e:
        logging.error(f"獲取溫度圖表資料時發生錯誤: {e}")
        return {'labels': [], 'data': []}

def get_humidity_chart_data(hours=24):
    """獲取濕度圖表資料"""
    try:
        if not database_manager:
            return {'labels': [], 'data': []}
        
        # 實作濕度資料查詢邏輯
        return {
            'labels': [],
            'data': [],
            'unit': '%'
        }
    except Exception as e:
        logging.error(f"獲取濕度圖表資料時發生錯誤: {e}")
        return {'labels': [], 'data': []}

def get_sensor_chart_data(hours=24):
    """獲取感測器圖表資料"""
    try:
        if not database_manager:
            return {'labels': [], 'datasets': []}
        
        # 實作感測器資料查詢邏輯
        return {
            'labels': [],
            'datasets': []
        }
    except Exception as e:
        logging.error(f"獲取感測器圖表資料時發生錯誤: {e}")
        return {'labels': [], 'datasets': []}

def get_recent_uart_data():
    """獲取最近的 UART 資料"""
    try:
        if not uart_reader:
            return []
        
        # 獲取最近的資料
        recent_data = getattr(uart_reader, 'recent_data', [])
        return recent_data[-10:] if recent_data else []  # 返回最近 10 筆
    except Exception as e:
        logging.error(f"獲取最近 UART 資料時發生錯誤: {e}")
        return []

def get_app_uptime():
    """獲取應用程式運行時間"""
    try:
        # 這裡應該實作運行時間計算
        return "運行中"
    except Exception as e:
        return "未知"

def get_uart_status():
    """獲取 UART 狀態"""
    try:
        if not uart_reader:
            return "未啟用"
        return "運行中" if getattr(uart_reader, 'is_reading', False) else "停止"
    except Exception as e:
        return "未知"

def get_database_status():
    """獲取資料庫狀態"""
    try:
        if not database_manager:
            return "未啟用"
        return "運行中"
    except Exception as e:
        return "未知"

def get_config_status():
    """獲取配置狀態"""
    try:
        if not config_manager:
            return "未載入"
        return "已載入"
    except Exception as e:
        return "未知"