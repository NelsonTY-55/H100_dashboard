"""
Dashboard API 控制器
處理 Dashboard API 的路由和請求邏輯
"""

from flask import Blueprint, jsonify, request
from datetime import datetime
import logging
from typing import Dict, Any

# 創建 Blueprint
dashboard_api_bp = Blueprint('dashboard_api', __name__)

# 導入模型
try:
    from models.dashboard_api_model import DashboardAPIModel
    from models.dashboard_model import DashboardModel
    from models.system_model import SystemModel
    MODELS_AVAILABLE = True
except ImportError as e:
    MODELS_AVAILABLE = False
    print(f"警告: 無法導入模型: {e}")

# 導入設定管理器
try:
    from config.config_manager import ConfigManager
    CONFIG_MANAGER_AVAILABLE = True
except ImportError as e:
    CONFIG_MANAGER_AVAILABLE = False
    print(f"警告: 無法導入 ConfigManager: {e}")

# 初始化模型
dashboard_api_model = DashboardAPIModel() if MODELS_AVAILABLE else None
dashboard_model = None
system_model = None
config_manager = None

try:
    if MODELS_AVAILABLE:
        dashboard_model = DashboardModel()
        system_model = SystemModel()
    if CONFIG_MANAGER_AVAILABLE:
        config_manager = ConfigManager()
except Exception as e:
    logging.error(f"初始化模型失敗: {e}")


class DashboardAPIController:
    """Dashboard API 控制器類"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    @staticmethod
    @dashboard_api_bp.route('/')
    def index():
        """API 服務首頁"""
        return jsonify({
            'service': 'H100 Dashboard API',
            'version': '1.0.0',
            'status': 'running',
            'endpoints': {
                'system': '/api/system',
                'dashboard': '/api/dashboard',
                'config': '/api/config',
                'health': '/api/health',
                'status': '/api/status'
            },
            'timestamp': datetime.now().isoformat()
        })
    
    @staticmethod
    @dashboard_api_bp.route('/api/health')
    def health_check():
        """健康檢查端點"""
        uptime = dashboard_api_model.get_uptime() if dashboard_api_model else "未知"
        return jsonify({
            'status': 'healthy',
            'service': 'dashboard-api',
            'timestamp': datetime.now().isoformat(),
            'uptime': uptime
        })
    
    @staticmethod
    @dashboard_api_bp.route('/api/system')
    def get_system_info():
        """取得系統資訊"""
        try:
            if dashboard_model:
                system_info = dashboard_model.get_system_info()
            elif dashboard_api_model:
                system_info = dashboard_api_model.get_basic_system_info()
            else:
                system_info = {'error': '無法取得系統資訊'}
                
            return jsonify({
                'success': True,
                'data': system_info,
                'timestamp': datetime.now().isoformat()
            })
        except Exception as e:
            logging.error(f"取得系統資訊失敗: {e}")
            return jsonify({
                'success': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }), 500
    
    @staticmethod
    @dashboard_api_bp.route('/api/dashboard')
    def get_dashboard_data():
        """取得儀表板資料"""
        try:
            if dashboard_api_model:
                dashboard_data = dashboard_api_model.get_dashboard_data()
            else:
                dashboard_data = {'error': '無法取得儀表板資料'}
                
            return jsonify({
                'success': True,
                'data': dashboard_data,
                'timestamp': datetime.now().isoformat()
            })
        except Exception as e:
            logging.error(f"取得儀表板資料失敗: {e}")
            return jsonify({
                'success': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }), 500
    
    @staticmethod
    @dashboard_api_bp.route('/api/config')
    def get_config():
        """取得設定資訊"""
        try:
            if config_manager:
                config_data = config_manager.get_all_configs()
            elif dashboard_api_model:
                config_data = dashboard_api_model.get_basic_config()
            else:
                config_data = {'error': '無法取得設定資訊'}
                
            return jsonify({
                'success': True,
                'data': config_data,
                'timestamp': datetime.now().isoformat()
            })
        except Exception as e:
            logging.error(f"取得設定資訊失敗: {e}")
            return jsonify({
                'success': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }), 500
    
    @staticmethod
    @dashboard_api_bp.route('/api/status')
    def get_service_status():
        """取得服務狀態"""
        try:
            if dashboard_api_model:
                status_data = dashboard_api_model.get_service_status()
            else:
                status_data = {
                    'api_service': 'running',
                    'note': '基本狀態資訊',
                    'last_update': datetime.now().isoformat()
                }
                
            return jsonify({
                'success': True,
                'data': status_data,
                'timestamp': datetime.now().isoformat()
            })
        except Exception as e:
            logging.error(f"取得服務狀態失敗: {e}")
            return jsonify({
                'success': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }), 500


# 錯誤處理
@dashboard_api_bp.errorhandler(404)
def not_found(error):
    """404 錯誤處理"""
    return jsonify({
        'success': False,
        'error': 'API 端點不存在',
        'code': 404,
        'timestamp': datetime.now().isoformat()
    }), 404

@dashboard_api_bp.errorhandler(500)
def internal_error(error):
    """500 錯誤處理"""
    return jsonify({
        'success': False,
        'error': '內部伺服器錯誤',
        'code': 500,
        'timestamp': datetime.now().isoformat()
    }), 500