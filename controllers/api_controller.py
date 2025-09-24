"""
API 控制器
處理一般 API 路由和系統狀態
"""

from flask import Blueprint, jsonify, request
import logging
from models import SystemModel, NetworkModel

# 創建 Blueprint
api_bp = Blueprint('api', __name__, url_prefix='/api')

# 初始化模型
system_model = SystemModel()
network_model = NetworkModel()


@api_bp.route('/health')
def api_health():
    """API 健康檢查"""
    try:
        return jsonify({
            'success': True,
            'status': 'healthy',
            'message': 'Dashboard API 服務正常運行',
            'timestamp': system_model.get_system_info()
        })
    except Exception as e:
        logging.error(f"健康檢查失敗: {e}")
        return jsonify({
            'success': False,
            'status': 'unhealthy',
            'error': str(e)
        }), 500


@api_bp.route('/status')
def api_status():
    """獲取系統狀態"""
    try:
        system_info = system_model.get_detailed_system_info()
        network_status = network_model.get_network_status()
        
        return jsonify({
            'success': True,
            'data': {
                'system': system_info,
                'network': network_status,
                'service': {
                    'name': 'H100 Dashboard',
                    'version': '1.0.0',
                    'status': 'running'
                }
            }
        })
        
    except Exception as e:
        logging.error(f"獲取系統狀態時發生錯誤: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@api_bp.route('/config')
def api_config():
    """獲取系統配置"""
    try:
        # 返回非敏感的配置資訊
        config = {
            'features': {
                'uart_support': True,
                'wifi_support': True,
                'multi_device': True,
                'system_monitoring': system_model.get_system_info()['psutil_available']
            },
            'limits': {
                'max_uart_records': 50000,
                'max_devices': 100,
                'api_timeout': 30
            }
        }
        
        return jsonify({
            'success': True,
            'data': config
        })
        
    except Exception as e:
        logging.error(f"獲取系統配置時發生錯誤: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@api_bp.route('/system/status')
def api_system_status():
    """獲取詳細系統狀態"""
    try:
        system_stats = system_model.get_system_stats()
        
        return jsonify({
            'success': True,
            'data': system_stats
        })
        
    except Exception as e:
        logging.error(f"獲取系統狀態時發生錯誤: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@api_bp.route('/system/offline-mode', methods=['POST'])
def api_system_offline_mode():
    """設定離線模式"""
    try:
        data = request.get_json()
        offline_mode = data.get('offline_mode', False)
        
        # 這裡可以實現離線模式的邏輯
        # 暫時只返回設定結果
        
        return jsonify({
            'success': True,
            'data': {
                'offline_mode': offline_mode,
                'message': f"離線模式已{'啟用' if offline_mode else '關閉'}"
            }
        })
        
    except Exception as e:
        logging.error(f"設定離線模式時發生錯誤: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500