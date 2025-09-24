"""
Dashboard 控制器
處理儀表板相關的路由和邏輯
"""

from flask import Blueprint, render_template, request, jsonify
import logging
from models import SystemModel, UartDataModel, DeviceSettingsModel

# 創建 Blueprint
dashboard_bp = Blueprint('dashboard', __name__)

# 初始化模型
system_model = SystemModel()
uart_model = UartDataModel()
device_model = DeviceSettingsModel()


@dashboard_bp.route('/dashboard')
def dashboard():
    """儀表板主頁"""
    try:
        # 獲取系統資訊
        system_info = system_model.get_system_info()
        
        # 獲取設備列表
        devices = device_model.get_all_devices()
        
        return render_template('dashboard.html', 
                             system_info=system_info,
                             devices=devices)
    except Exception as e:
        logging.error(f"載入儀表板時發生錯誤: {e}")
        return render_template('error.html', error=str(e)), 500


@dashboard_bp.route('/data-analysis')
def data_analysis():
    """數據分析頁面"""
    try:
        return render_template('11.html')
    except Exception as e:
        logging.error(f"載入數據分析頁面時發生錯誤: {e}")
        return render_template('error.html', error=str(e)), 500


@dashboard_bp.route('/11')
def page_11():
    """11頁面"""
    try:
        return render_template('11.html')
    except Exception as e:
        logging.error(f"載入11頁面時發生錯誤: {e}")
        return render_template('error.html', error=str(e)), 500


@dashboard_bp.route('/api/dashboard/stats')
def api_dashboard_stats():
    """獲取儀表板統計資訊"""
    try:
        # 獲取系統統計
        system_stats = system_model.get_system_stats()
        
        # 獲取UART數據統計
        uart_data = uart_model.get_uart_data_from_files(limit=100)
        
        # 獲取設備統計
        devices = device_model.get_all_devices()
        device_count = len(devices)
        
        stats = {
            'system': system_stats,
            'uart': {
                'success': uart_data['success'],
                'total_records': uart_data.get('total_count', 0),
                'files_read': uart_data.get('files_read', 0)
            },
            'devices': {
                'total_count': device_count,
                'devices': devices
            }
        }
        
        return jsonify({
            'success': True,
            'data': stats
        })
        
    except Exception as e:
        logging.error(f"獲取儀表板統計資訊時發生錯誤: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@dashboard_bp.route('/api/dashboard/areas')
def api_dashboard_areas():
    """獲取區域資訊"""
    try:
        # 這裡可以從資料庫或配置文件獲取區域資訊
        # 暫時返回示例數據
        areas = [
            {
                'id': 'area_1',
                'name': '生產區域 A',
                'device_count': 5,
                'status': 'active'
            },
            {
                'id': 'area_2', 
                'name': '生產區域 B',
                'device_count': 3,
                'status': 'active'
            }
        ]
        
        return jsonify({
            'success': True,
            'data': areas
        })
        
    except Exception as e:
        logging.error(f"獲取區域資訊時發生錯誤: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@dashboard_bp.route('/api/dashboard/device-settings')
def api_dashboard_device_settings():
    """獲取設備設定資訊"""
    try:
        device_settings = device_model.load_device_settings()
        multi_device_settings = device_model.load_multi_device_settings()
        
        return jsonify({
            'success': True,
            'data': {
                'device_settings': device_settings,
                'multi_device_settings': multi_device_settings
            }
        })
        
    except Exception as e:
        logging.error(f"獲取設備設定資訊時發生錯誤: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@dashboard_bp.route('/api/dashboard/chart-data')
def api_dashboard_chart_data():
    """獲取圖表數據"""
    try:
        # 獲取指定MAC ID的數據（如果有提供）
        mac_id = request.args.get('mac_id')
        limit = int(request.args.get('limit', 100))
        
        uart_data = uart_model.get_uart_data_from_files(mac_id=mac_id, limit=limit)
        
        if not uart_data['success']:
            return jsonify({
                'success': False,
                'error': uart_data['error']
            }), 400
        
        # 處理圖表數據格式
        chart_data = []
        for record in uart_data['data']:
            chart_point = {
                'timestamp': record.get('timestamp'),
                'temperature': record.get('temperature'),
                'humidity': record.get('humidity'),
                'mac_id': record.get('mac_id'),
                'channel': record.get('channel'),
                'rssi': record.get('rssi')
            }
            chart_data.append(chart_point)
        
        return jsonify({
            'success': True,
            'data': chart_data,
            'total_count': len(chart_data),
            'mac_filter': mac_id
        })
        
    except Exception as e:
        logging.error(f"獲取圖表數據時發生錯誤: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@dashboard_bp.route('/api/dashboard/devices')
def api_dashboard_devices():
    """獲取設備列表"""
    try:
        devices = device_model.get_all_devices()
        
        # 豐富設備資訊（添加狀態等）
        enriched_devices = []
        for device in devices:
            device_info = device.copy()
            # 可以在這裡添加設備狀態檢查邏輯
            device_info['online_status'] = 'unknown'  # 預設狀態
            enriched_devices.append(device_info)
        
        return jsonify({
            'success': True,
            'data': enriched_devices,
            'total_count': len(enriched_devices)
        })
        
    except Exception as e:
        logging.error(f"獲取設備列表時發生錯誤: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@dashboard_bp.route('/api/dashboard/overview')
def api_dashboard_overview():
    """獲取儀表板概覽資訊"""
    try:
        # 獲取系統資訊
        system_info = system_model.get_detailed_system_info()
        
        # 獲取UART數據概覽
        uart_data = uart_model.get_uart_data_from_files(limit=10)
        mac_ids = uart_model.get_mac_ids()
        
        # 獲取設備概覽
        devices = device_model.get_all_devices()
        
        overview = {
            'system': system_info,
            'uart': {
                'total_mac_ids': len(mac_ids),
                'mac_ids': mac_ids[:5],  # 只顯示前5個
                'recent_data_count': uart_data.get('total_count', 0),
                'data_available': uart_data['success']
            },
            'devices': {
                'total_count': len(devices),
                'recent_devices': devices[:3] if devices else []  # 只顯示前3個
            }
        }
        
        return jsonify({
            'success': True,
            'data': overview
        })
        
    except Exception as e:
        logging.error(f"獲取儀表板概覽時發生錯誤: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500