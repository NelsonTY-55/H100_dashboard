"""
API 控制器
處理一般 API 路由和系統狀態
"""

from flask import Blueprint, jsonify, request
import logging
import os
import platform
from datetime import datetime

# 創建 Blueprint
api_bp = Blueprint('api', __name__)

# 全域變數，將在初始化時設置
config = None
import_manager = None

def init_controller(config_obj, import_manager_obj):
    """初始化控制器"""
    global config, import_manager
    config = config_obj
    import_manager = import_manager_obj

def get_system_info():
    """獲取系統基本資訊"""
    return {
        'platform': platform.system(),
        'platform_version': platform.release(),
        'python_version': platform.python_version(),
        'working_directory': os.getcwd(),
        'psutil_available': import_manager.is_available('psutil') if import_manager else False
    }

@api_bp.route('/health')
def health_check():
    """健康檢查 API"""
    return jsonify({
        'status': 'healthy',
        'service': 'Dashboard API (MVC)',
        'timestamp': datetime.now().isoformat(),
        'system_info': get_system_info()
    })

@api_bp.route('/status')
def status():
    """服務狀態 API"""
    try:
        return jsonify({
            'success': True,
            'service': 'Dashboard API (MVC)',
            'version': '1.0.0',
            'uptime': datetime.now().isoformat(),
            'psutil_available': import_manager.is_available('psutil') if import_manager else False,
            'system_info': get_system_info()
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'狀態檢查失敗: {str(e)}'
        })

@api_bp.route('/dashboard/config', methods=['GET'])
def get_dashboard_config():
    """API: 獲取 Dashboard 配置"""
    return jsonify({
        'success': True,
        'config': {
            'raspberry_pi_host': config.RASPBERRY_PI_HOST if config else 'N/A',
            'raspberry_pi_port': config.RASPBERRY_PI_PORT if config else 'N/A',
            'standalone_mode': config.STANDALONE_MODE if config else True,
            'requests_available': import_manager.is_available('requests') if import_manager else False,
        },
        'timestamp': datetime.now().isoformat()
    })

@api_bp.route('/dashboard/config', methods=['POST'])
def update_dashboard_config():
    """API: 更新 Dashboard 配置"""
    try:
        data = request.get_json()
        
        if not config:
            return jsonify({
                'success': False,
                'message': '配置管理器未初始化'
            })
        
        if 'raspberry_pi_host' in data:
            config.RASPBERRY_PI_HOST = data['raspberry_pi_host']
            
        if 'raspberry_pi_port' in data:
            config.RASPBERRY_PI_PORT = int(data['raspberry_pi_port'])
            
        logging.getLogger(__name__).info(f"Dashboard 配置已更新: {config.RASPBERRY_PI_HOST}:{config.RASPBERRY_PI_PORT}")
        
        return jsonify({
            'success': True,
            'message': '配置已更新',
            'config': {
                'raspberry_pi_host': config.RASPBERRY_PI_HOST,
                'raspberry_pi_port': config.RASPBERRY_PI_PORT,
                'standalone_mode': config.STANDALONE_MODE
            }
        })
        
    except Exception as e:
        logging.getLogger(__name__).error(f"更新 Dashboard 配置失敗: {e}")
        return jsonify({
            'success': False,
            'message': f'更新配置失敗: {str(e)}'
        })
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