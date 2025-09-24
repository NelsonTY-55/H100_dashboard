"""
Flask 應用程式工廠
使用工廠模式創建和配置 Flask 應用程式
"""

from flask import Flask
import os
import logging
from datetime import datetime


def create_app(config=None):
    """
    Flask 應用程式工廠函數
    
    Args:
        config: 配置對象或配置字典
        
    Returns:
        Flask: 配置好的 Flask 應用程式實例
    """
    app = Flask(__name__)
    
    # 設定秘密金鑰
    app.secret_key = config.get('SECRET_KEY', 'dashboard_secret_key_2025') if config else 'dashboard_secret_key_2025'
    
    # 配置應用程式
    configure_app(app, config)
    
    # 設定日誌
    configure_logging(app)
    
    # 註冊 Blueprint
    register_blueprints(app)
    
    # 註冊錯誤處理器
    register_error_handlers(app)
    
    # 註冊上下文處理器
    register_context_processors(app)
    
    return app


def configure_app(app, config=None):
    """配置應用程式設定"""
    # 預設配置
    default_config = {
        'DEBUG': True,
        'HOST': '0.0.0.0',
        'PORT': 5001,
        'TEMPLATES_AUTO_RELOAD': True,
        'JSON_AS_ASCII': False,
        'JSON_SORT_KEYS': False
    }
    
    # 套用預設配置
    for key, value in default_config.items():
        app.config.setdefault(key, value)
    
    # 套用自定義配置
    if config:
        if isinstance(config, dict):
            app.config.update(config)
        else:
            app.config.from_object(config)
    
    # 從環境變數載入配置
    app.config.from_prefixed_env('DASHBOARD')


def configure_logging(app):
    """配置日誌系統"""
    if not app.debug:
        # 生產環境日誌配置
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s [%(levelname)s] [Dashboard] %(message)s',
            handlers=[
                logging.FileHandler('dashboard.log'),
                logging.StreamHandler()
            ]
        )
    else:
        # 開發環境日誌配置
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s [%(levelname)s] [Dashboard] %(message)s',
            handlers=[
                logging.StreamHandler()
            ]
        )
    
    app.logger.info('Dashboard 應用程式日誌系統已初始化')


def register_blueprints(app):
    """註冊所有 Blueprint"""
    try:
        # 註冊原有的 Blueprint
        from controllers import (dashboard_bp, api_bp, device_bp, uart_bp, 
                               network_bp, protocol_bp, ftp_bp, database_bp, mode_bp)
        
        app.register_blueprint(dashboard_bp)
        app.register_blueprint(api_bp)
        app.register_blueprint(device_bp)
        app.register_blueprint(uart_bp)
        app.register_blueprint(network_bp)
        app.register_blueprint(protocol_bp)
        app.register_blueprint(ftp_bp)
        app.register_blueprint(database_bp)
        app.register_blueprint(mode_bp)
        
        # 註冊新的 app_integrated.py 重構後的 Blueprint
        from controllers.integrated_home_controller import integrated_home_bp
        from controllers.integrated_device_controller import integrated_device_bp
        from controllers.integrated_wifi_controller import integrated_wifi_bp
        from controllers.integrated_dashboard_controller import integrated_dashboard_bp
        from controllers.integrated_protocol_controller import integrated_protocol_bp
        from controllers.integrated_uart_controller import integrated_uart_bp
        
        app.register_blueprint(integrated_home_bp)
        app.register_blueprint(integrated_device_bp)
        app.register_blueprint(integrated_wifi_bp)
        app.register_blueprint(integrated_dashboard_bp)
        app.register_blueprint(integrated_protocol_bp)
        app.register_blueprint(integrated_uart_bp)
        
        app.logger.info('所有 Blueprint 已成功註冊')
        
    except ImportError as e:
        app.logger.error(f'註冊 Blueprint 時發生錯誤: {e}')
        raise


def register_error_handlers(app):
    """註冊錯誤處理器"""
    from views import TemplateView, ApiResponseView
    from flask import request, jsonify
    
    @app.errorhandler(404)
    def not_found_error(error):
        """處理 404 錯誤"""
        if request.path.startswith('/api/'):
            return ApiResponseView.not_found()
        return TemplateView.render_404_page(), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        """處理 500 錯誤"""
        app.logger.error(f'內部伺服器錯誤: {error}')
        if request.path.startswith('/api/'):
            return ApiResponseView.internal_error(error)
        return TemplateView.render_error_page('內部伺服器錯誤', 500), 500
    
    @app.errorhandler(403)
    def forbidden_error(error):
        """處理 403 錯誤"""
        if request.path.startswith('/api/'):
            return ApiResponseView.forbidden()
        return TemplateView.render_error_page('禁止訪問', 403), 403
    
    @app.errorhandler(400)
    def bad_request_error(error):
        """處理 400 錯誤"""
        if request.path.startswith('/api/'):
            return ApiResponseView.error('請求格式錯誤', 400)
        return TemplateView.render_error_page('請求格式錯誤', 400), 400


def register_context_processors(app):
    """註冊上下文處理器"""
    from flask import request
    
    @app.context_processor
    def inject_global_vars():
        """注入全域變數到模板"""
        return {
            'app_name': 'H100 Dashboard',
            'app_version': '2.0.0',
            'current_time': datetime.now(),
            'debug_mode': app.debug
        }
    
    @app.before_request
    def before_request():
        """請求前處理"""
        app.logger.debug(f'處理請求: {request.method} {request.path}')
    
    @app.after_request
    def after_request(response):
        """請求後處理"""
        app.logger.debug(f'回應狀態: {response.status_code}')
        
        # 設定 CORS 標頭（如果需要）
        if app.config.get('ENABLE_CORS', False):
            response.headers['Access-Control-Allow-Origin'] = '*'
            response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
            response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
        
        return response


def initialize_services(app):
    """初始化外部服務和依賴"""
    with app.app_context():
        try:
            # 初始化資料庫連接（如果需要）
            app.logger.info('正在初始化服務...')
            
            # 檢查必要的目錄是否存在
            required_dirs = ['History', 'logs', 'config']
            for dir_name in required_dirs:
                dir_path = os.path.join(os.getcwd(), dir_name)
                if not os.path.exists(dir_path):
                    os.makedirs(dir_path)
                    app.logger.info(f'創建目錄: {dir_path}')
            
            # 檢查必要的檔案
            required_files = ['device_settings.json', 'multi_device_settings.json']
            for file_name in required_files:
                file_path = os.path.join(os.getcwd(), file_name)
                if not os.path.exists(file_path):
                    # 創建空的 JSON 檔案
                    import json
                    with open(file_path, 'w', encoding='utf-8') as f:
                        json.dump({}, f, ensure_ascii=False, indent=2)
                    app.logger.info(f'創建檔案: {file_path}')
            
            app.logger.info('服務初始化完成')
            
        except Exception as e:
            app.logger.error(f'服務初始化失敗: {e}')
            raise


# 添加一些實用的裝飾器
def require_json(f):
    """要求 JSON 內容類型的裝飾器"""
    from functools import wraps
    from flask import request, jsonify
    
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not request.is_json:
            return jsonify({'error': '需要 JSON 內容類型'}), 400
        return f(*args, **kwargs)
    return decorated_function


def validate_json_fields(required_fields):
    """驗證 JSON 字段的裝飾器"""
    def decorator(f):
        from functools import wraps
        from flask import request, jsonify
        
        @wraps(f)
        def decorated_function(*args, **kwargs):
            data = request.get_json()
            if not data:
                return jsonify({'error': '沒有接收到 JSON 數據'}), 400
            
            missing_fields = [field for field in required_fields if field not in data]
            if missing_fields:
                return jsonify({
                    'error': '缺少必要字段',
                    'missing_fields': missing_fields
                }), 400
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator