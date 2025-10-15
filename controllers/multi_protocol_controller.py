"""
多協定控制器
與 RAS_pi 系統同步的多協定管理 API
"""

from flask import Blueprint, jsonify, request
import logging

# 創建 Blueprint
multi_protocol_bp = Blueprint('multi_protocol', __name__)

@multi_protocol_bp.route('/protocols')
def list_protocols():
    """列出所有支援的協定"""
    try:
        protocols = [
            {
                'name': 'MQTT',
                'enabled': True,
                'status': 'active',
                'description': 'Message Queuing Telemetry Transport'
            },
            {
                'name': 'HTTP',
                'enabled': True,
                'status': 'active',
                'description': 'HyperText Transfer Protocol'
            },
            {
                'name': 'WebSocket',
                'enabled': False,
                'status': 'inactive',
                'description': 'WebSocket Protocol'
            },
            {
                'name': 'TCP',
                'enabled': True,
                'status': 'active',
                'description': 'Transmission Control Protocol'
            }
        ]
        
        return jsonify({
            'success': True,
            'protocols': protocols,
            'count': len(protocols)
        })
        
    except Exception as e:
        logging.error(f"列出協定失敗: {e}")
        return jsonify({
            'success': False,
            'message': f'列出協定失敗: {str(e)}'
        }), 500

@multi_protocol_bp.route('/status')
def protocols_status():
    """獲取所有協定狀態"""
    try:
        status = {
            'active_protocols': ['MQTT', 'HTTP', 'TCP'],
            'inactive_protocols': ['WebSocket'],
            'total_connections': 3,
            'error_count': 0
        }
        
        return jsonify({
            'success': True,
            'status': status
        })
        
    except Exception as e:
        logging.error(f"獲取協定狀態失敗: {e}")
        return jsonify({
            'success': False,
            'message': f'獲取協定狀態失敗: {str(e)}'
        }), 500

@multi_protocol_bp.route('/enable/<protocol>', methods=['POST'])
def enable_protocol(protocol):
    """啟用指定協定"""
    try:
        # 模擬協定啟用
        valid_protocols = ['mqtt', 'http', 'websocket', 'tcp']
        
        if protocol.lower() not in valid_protocols:
            return jsonify({
                'success': False,
                'message': f'不支援的協定: {protocol}'
            }), 400
        
        return jsonify({
            'success': True,
            'message': f'協定 {protocol} 已啟用',
            'protocol': protocol
        })
        
    except Exception as e:
        logging.error(f"啟用協定失敗: {e}")
        return jsonify({
            'success': False,
            'message': f'啟用協定失敗: {str(e)}'
        }), 500

@multi_protocol_bp.route('/disable/<protocol>', methods=['POST'])
def disable_protocol(protocol):
    """停用指定協定"""
    try:
        # 模擬協定停用
        valid_protocols = ['mqtt', 'http', 'websocket', 'tcp']
        
        if protocol.lower() not in valid_protocols:
            return jsonify({
                'success': False,
                'message': f'不支援的協定: {protocol}'
            }), 400
        
        return jsonify({
            'success': True,
            'message': f'協定 {protocol} 已停用',
            'protocol': protocol
        })
        
    except Exception as e:
        logging.error(f"停用協定失敗: {e}")
        return jsonify({
            'success': False,
            'message': f'停用協定失敗: {str(e)}'
        }), 500

@multi_protocol_bp.route('/config/<protocol>')
def get_protocol_config(protocol):
    """獲取協定配置"""
    try:
        # 模擬協定配置
        config = {
            'protocol': protocol,
            'enabled': True,
            'settings': {
                'timeout': 30,
                'retries': 3,
                'buffer_size': 1024
            },
            'endpoints': []
        }
        
        return jsonify({
            'success': True,
            'config': config
        })
        
    except Exception as e:
        logging.error(f"獲取協定配置失敗: {e}")
        return jsonify({
            'success': False,
            'message': f'獲取協定配置失敗: {str(e)}'
        }), 500

@multi_protocol_bp.route('/config/<protocol>', methods=['POST'])
def update_protocol_config(protocol):
    """更新協定配置"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'message': '無效的配置數據'
            }), 400
        
        # 模擬配置更新
        return jsonify({
            'success': True,
            'message': f'協定 {protocol} 配置已更新',
            'protocol': protocol,
            'config': data
        })
        
    except Exception as e:
        logging.error(f"更新協定配置失敗: {e}")
        return jsonify({
            'success': False,
            'message': f'更新協定配置失敗: {str(e)}'
        }), 500