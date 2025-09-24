# controllers/integrated_wifi_controller.py
from flask import Blueprint, render_template, request, jsonify
import logging

# 創建 Blueprint
integrated_wifi_bp = Blueprint('integrated_wifi', __name__)


@integrated_wifi_bp.route('/wifi')
def wifi_setting():
    """WiFi 設定頁面"""
    logging.info(f'訪問 WiFi 設定頁面, remote_addr={request.remote_addr}')
    return render_template('wifi.html')


@integrated_wifi_bp.route('/api/wifi/scan', methods=['GET','POST'])
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


@integrated_wifi_bp.route('/api/wifi/connect', methods=['POST'])
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


@integrated_wifi_bp.route('/api/wifi/status')
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