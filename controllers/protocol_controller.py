"""
協議控制器
處理協議管理相關的路由
"""

from flask import Blueprint, request, jsonify
import logging
from datetime import datetime

# 創建 Blueprint
protocol_bp = Blueprint('protocol', __name__, url_prefix='/api')

# 全域變數（這些應該從原始程式碼移過來）
protocol_manager = None


@protocol_bp.route('/protocols')
def api_protocols():
    """獲取可用協議列表"""
    try:
        # 返回支援的協議列表
        protocols = [
            {
                'name': 'UART',
                'description': 'UART 串口通訊協議',
                'status': 'available',
                'version': '1.0'
            },
            {
                'name': 'HTTP',
                'description': 'HTTP 網路通訊協議',
                'status': 'available',
                'version': '1.1'
            },
            {
                'name': 'TCP',
                'description': 'TCP Socket 通訊協議',
                'status': 'available',
                'version': '1.0'
            }
        ]
        
        return jsonify({
            'success': True,
            'data': protocols,
            'total_count': len(protocols)
        })
        
    except Exception as e:
        logging.error(f"獲取協議列表時發生錯誤: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@protocol_bp.route('/protocol-config/<protocol>')
def api_protocol_config(protocol):
    """獲取指定協議的配置"""
    try:
        # 根據協議類型返回配置
        configs = {
            'uart': {
                'port': '/dev/ttyUSB0',
                'baudrate': 9600,
                'timeout': 1,
                'data_bits': 8,
                'stop_bits': 1,
                'parity': 'none'
            },
            'http': {
                'host': 'localhost',
                'port': 80,
                'timeout': 30,
                'max_retries': 3,
                'ssl_verify': True
            },
            'tcp': {
                'host': 'localhost',
                'port': 8080,
                'timeout': 30,
                'keep_alive': True,
                'buffer_size': 1024
            }
        }
        
        protocol_lower = protocol.lower()
        if protocol_lower in configs:
            return jsonify({
                'success': True,
                'data': {
                    'protocol': protocol,
                    'config': configs[protocol_lower]
                }
            })
        else:
            return jsonify({
                'success': False,
                'error': f'不支援的協議: {protocol}'
            }), 404
        
    except Exception as e:
        logging.error(f"獲取協議配置時發生錯誤: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@protocol_bp.route('/active-protocol', methods=['GET', 'POST'])
def api_active_protocol():
    """獲取或設定活動協議"""
    try:
        if request.method == 'GET':
            # 獲取當前活動協議
            active_protocol = {
                'name': 'UART',  # 預設協議
                'status': 'active',
                'start_time': datetime.now().isoformat(),
                'config': {
                    'port': '/dev/ttyUSB0',
                    'baudrate': 9600
                }
            }
            
            return jsonify({
                'success': True,
                'data': active_protocol
            })
        
        elif request.method == 'POST':
            # 設定活動協議
            data = request.get_json()
            if not data:
                return jsonify({
                    'success': False,
                    'error': '沒有接收到協議數據'
                }), 400
            
            protocol_name = data.get('protocol')
            if not protocol_name:
                return jsonify({
                    'success': False,
                    'error': '缺少協議名稱'
                }), 400
            
            # 這裡應該實現實際的協議切換邏輯
            
            return jsonify({
                'success': True,
                'message': f'已切換到協議: {protocol_name}',
                'data': {
                    'protocol': protocol_name,
                    'status': 'active',
                    'switch_time': datetime.now().isoformat()
                }
            })
        
    except Exception as e:
        logging.error(f"處理活動協議時發生錯誤: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@protocol_bp.route('/protocol/status', methods=['GET'])
def api_protocol_status():
    """獲取協議狀態"""
    try:
        protocol_status = {
            'uart': {
                'status': 'active',
                'connected': True,
                'last_activity': datetime.now().isoformat(),
                'error_count': 0
            },
            'http': {
                'status': 'inactive',
                'connected': False,
                'last_activity': None,
                'error_count': 0
            },
            'tcp': {
                'status': 'inactive',
                'connected': False,
                'last_activity': None,
                'error_count': 0
            }
        }
        
        return jsonify({
            'success': True,
            'data': protocol_status
        })
        
    except Exception as e:
        logging.error(f"獲取協議狀態時發生錯誤: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@protocol_bp.route('/protocol/configured-status', methods=['GET'])
def api_protocol_configured_status():
    """獲取協議配置狀態"""
    try:
        configured_status = {
            'protocols_configured': 3,
            'protocols_active': 1,
            'configuration_valid': True,
            'last_config_update': datetime.now().isoformat(),
            'details': [
                {
                    'protocol': 'UART',
                    'configured': True,
                    'valid': True,
                    'active': True
                },
                {
                    'protocol': 'HTTP',
                    'configured': True,
                    'valid': True,
                    'active': False
                },
                {
                    'protocol': 'TCP',
                    'configured': True,
                    'valid': True,
                    'active': False
                }
            ]
        }
        
        return jsonify({
            'success': True,
            'data': configured_status
        })
        
    except Exception as e:
        logging.error(f"獲取協議配置狀態時發生錯誤: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@protocol_bp.route('/protocol/start', methods=['POST'])
def api_protocol_start():
    """啟動協議"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': '沒有接收到啟動數據'
            }), 400
        
        protocol = data.get('protocol')
        config = data.get('config', {})
        
        if not protocol:
            return jsonify({
                'success': False,
                'error': '缺少協議名稱'
            }), 400
        
        # 這裡應該實現實際的協議啟動邏輯
        
        return jsonify({
            'success': True,
            'message': f'協議 {protocol} 啟動成功',
            'data': {
                'protocol': protocol,
                'status': 'started',
                'start_time': datetime.now().isoformat(),
                'config': config
            }
        })
        
    except Exception as e:
        logging.error(f"啟動協議時發生錯誤: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500