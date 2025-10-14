"""
API 控制器 - MVC 架構
處理一般 API 路由 (健康檢查、狀態、配置等)
"""

from flask import Blueprint, request, jsonify
import logging
import platform
from datetime import datetime

# 創建 Blueprint
api_bp = Blueprint('api', __name__)

# 全域變數，將在初始化時設置
config_manager = None
device_settings_manager = None

def init_controller(config_mgr, device_settings_mgr):
    """初始化控制器"""
    global config_manager, device_settings_manager
    config_manager = config_mgr
    device_settings_manager = device_settings_mgr

@api_bp.route('/health')
def health_check():
    """健康檢查 API"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'service': 'H100 Dashboard API',
        'version': '1.0.0'
    })

@api_bp.route('/status')
def status():
    """系統狀態 API"""
    try:
        system_info = get_system_info()
        
        return jsonify({
            'success': True,
            'timestamp': datetime.now().isoformat(),
            'data': {
                'system': system_info,
                'config': {
                    'host': '0.0.0.0',
                    'port': 5001,
                    'debug': True,
                    'standalone_mode': True
                },
                'service': {
                    'name': 'H100 Dashboard API',
                    'version': '1.0.0',
                    'status': 'running'
                }
            }
        })
        
    except Exception as e:
        logging.error(f"獲取系統狀態時發生錯誤: {e}")
        return jsonify({
            'success': False,
            'message': f'獲取系統狀態失敗: {str(e)}'
        })

@api_bp.route('/dashboard/config', methods=['GET', 'POST'])
def dashboard_config():
    """Dashboard 配置管理 API"""
    if request.method == 'GET':
        try:
            # 獲取當前配置
            config_data = {
                'raspberry_pi_host': '192.168.113.239',
                'raspberry_pi_port': 5000,
                'standalone_mode': True,
                'debug': True,
                'host': '0.0.0.0',
                'port': 5001
            }
            
            return jsonify({
                'success': True,
                'config': config_data,
                'timestamp': datetime.now().isoformat()
            })
            
        except Exception as e:
            logging.error(f"獲取 Dashboard 配置時發生錯誤: {e}")
            return jsonify({
                'success': False,
                'message': f'獲取配置失敗: {str(e)}'
            })
    
    else:  # POST
        try:
            data = request.get_json()
            if not data:
                return jsonify({
                    'success': False,
                    'message': '無效的請求資料'
                })
            
            # 這裡可以添加配置更新邏輯
            logging.info(f"Dashboard 配置更新請求: {data}")
            
            return jsonify({
                'success': True,
                'message': '配置已更新',
                'config': data,
                'timestamp': datetime.now().isoformat()
            })
            
        except Exception as e:
            logging.error(f"更新 Dashboard 配置時發生錯誤: {e}")
            return jsonify({
                'success': False,
                'message': f'更新配置失敗: {str(e)}'
            })

def get_system_info():
    """獲取系統基本資訊"""
    try:
        return {
            'platform': platform.system(),
            'platform_version': platform.release(),
            'python_version': platform.python_version(),
            'hostname': platform.node(),
            'architecture': platform.machine()
        }
    except Exception as e:
        logging.error(f"獲取系統資訊時發生錯誤: {e}")
        return {
            'platform': '未知',
            'platform_version': '未知',
            'python_version': '未知',
            'hostname': '未知',
            'architecture': '未知'
        }