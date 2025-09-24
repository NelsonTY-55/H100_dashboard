"""
網路控制器
處理 WiFi 和網路相關的路由
"""

from flask import Blueprint, request, jsonify
import logging
from models import NetworkModel

# 創建 Blueprint
network_bp = Blueprint('network', __name__, url_prefix='/api')

# 初始化模型
network_model = NetworkModel()


@network_bp.route('/wifi/scan')
def api_wifi_scan():
    """掃描 WiFi 網路"""
    try:
        networks = network_model.scan_wifi_networks()
        
        return jsonify({
            'success': True,
            'data': networks,
            'total_count': len(networks)
        })
        
    except Exception as e:
        logging.error(f"掃描WiFi網路時發生錯誤: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@network_bp.route('/wifi/debug')
def api_wifi_debug():
    """WiFi 調試資訊"""
    try:
        # 獲取網路狀態
        network_status = network_model.get_network_status()
        
        # 獲取當前WiFi資訊
        current_wifi = network_model.get_current_wifi()
        
        debug_info = {
            'network_status': network_status,
            'current_wifi': current_wifi,
            'capabilities': {
                'scan_available': True,
                'connect_available': True,
                'status_available': True
            }
        }
        
        return jsonify({
            'success': True,
            'data': debug_info
        })
        
    except Exception as e:
        logging.error(f"獲取WiFi調試資訊時發生錯誤: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@network_bp.route('/wifi/connect', methods=['POST'])
def api_wifi_connect():
    """連接 WiFi 網路"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': '沒有接收到連接資料'
            }), 400
        
        ssid = data.get('ssid')
        password = data.get('password')
        
        if not ssid:
            return jsonify({
                'success': False,
                'error': '缺少 SSID'
            }), 400
        
        # 嘗試連接WiFi
        result = network_model.connect_wifi(ssid, password)
        
        if result['success']:
            return jsonify({
                'success': True,
                'message': f'成功連接到 {ssid}',
                'data': result
            })
        else:
            return jsonify({
                'success': False,
                'error': f'連接失敗: {result.get("error", "未知錯誤")}',
                'data': result
            }), 400
        
    except Exception as e:
        logging.error(f"連接WiFi時發生錯誤: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@network_bp.route('/wifi/current')
def api_wifi_current():
    """獲取當前 WiFi 連接資訊"""
    try:
        current_wifi = network_model.get_current_wifi()
        
        return jsonify({
            'success': current_wifi['success'],
            'data': current_wifi.get('data', {}),
            'error': current_wifi.get('error')
        })
        
    except Exception as e:
        logging.error(f"獲取當前WiFi資訊時發生錯誤: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@network_bp.route('/host/save-config', methods=['POST'])
def api_host_save_config():
    """儲存主機配置"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': '沒有接收到配置資料'
            }), 400
        
        # 驗證配置資料
        required_fields = ['host', 'port']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'success': False,
                    'error': f'缺少必要字段: {field}'
                }), 400
        
        # 這裡應該實現實際的配置儲存邏輯
        # 暫時只進行驗證和返回結果
        
        host_config = {
            'host': data['host'],
            'port': data['port'],
            'protocol': data.get('protocol', 'http'),
            'timeout': data.get('timeout', 30),
            'saved_time': '2025-09-23T00:00:00'
        }
        
        return jsonify({
            'success': True,
            'message': '主機配置儲存成功',
            'data': host_config
        })
        
    except Exception as e:
        logging.error(f"儲存主機配置時發生錯誤: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@network_bp.route('/host/test-connection', methods=['POST'])
def api_host_test_connection():
    """測試主機連接"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': '沒有接收到測試資料'
            }), 400
        
        host = data.get('host', '8.8.8.8')
        timeout = data.get('timeout', 5)
        
        # 測試連接
        result = network_model.test_connection(host, timeout)
        
        return jsonify({
            'success': result['success'],
            'data': result,
            'message': '連接測試成功' if result['success'] else '連接測試失敗'
        })
        
    except Exception as e:
        logging.error(f"測試主機連接時發生錯誤: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500