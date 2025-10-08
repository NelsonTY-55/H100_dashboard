"""
Dashboard API 服務 - 重構版本
獨立的 Dashboard 和設備設定管理 API 服務
使用 MVC 架構
"""

from flask import Flask
import os
import json
import logging
import sys
from datetime import datetime

# 設置日誌
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# 修復 charset_normalizer 循環導入問題
if 'charset_normalizer' in sys.modules:
    del sys.modules['charset_normalizer']

# 創建 Flask 應用程式
app = Flask(__name__)
app.secret_key = 'dashboard_secret_key_2024'

# 全域變數
DATABASE_AVAILABLE = False
db_manager = None
uart_reader = None
protocol_manager = None
device_settings_manager = None
multi_device_settings_manager = None
config_manager = None

def initialize_dependencies():
    """初始化依賴項"""
    global DATABASE_AVAILABLE, db_manager, uart_reader, protocol_manager
    global device_settings_manager, multi_device_settings_manager, config_manager
    
    try:
        # 導入配置管理器
        from config.config_manager import ConfigManager
        config_manager = ConfigManager()
        print("Dashboard: 配置管理器載入成功")
    except ImportError as e:
        print(f"Dashboard: 配置管理器載入失敗: {e}")
        config_manager = None
    
    try:
        # 導入 UART 和協定管理器
        from uart_integrated import uart_reader as ur, protocol_manager as pm
        uart_reader = ur
        protocol_manager = pm
        print("Dashboard: UART 和協定管理器載入成功")
    except ImportError as e:
        print(f"Dashboard: UART 和協定管理器載入失敗: {e}")
        uart_reader = None
        protocol_manager = None
    
    try:
        # 導入設備設定管理器
        from device_settings import DeviceSettingsManager
        device_settings_manager = DeviceSettingsManager()
        print("Dashboard: 設備設定管理器載入成功")
    except ImportError as e:
        print(f"Dashboard: 設備設定管理器載入失敗: {e}")
        device_settings_manager = None
    
    try:
        # 導入多設備設定管理器
        from multi_device_settings import MultiDeviceSettingsManager
        multi_device_settings_manager = MultiDeviceSettingsManager()
        print("Dashboard: 多設備設定管理器載入成功")
    except ImportError as e:
        print(f"Dashboard: 多設備設定管理器載入失敗: {e}")
        multi_device_settings_manager = None
    
    try:
        # 導入資料庫管理器
        from database_manager import db_manager as dm
        db_manager = dm
        DATABASE_AVAILABLE = True
        print("Dashboard: 資料庫管理器載入成功")
    except ImportError as e:
        print(f"Dashboard: 資料庫管理器載入失敗: {e}")
        DATABASE_AVAILABLE = False
        db_manager = None

def register_blueprints():
    """註冊 Blueprint"""
    try:
        # 導入並註冊 Dashboard 控制器
        from controllers.dashboard_controller import dashboard_bp, init_controller
        
        # 初始化控制器
        init_controller(db_manager=db_manager, uart_reader=uart_reader)
        
        # 註冊 Blueprint
        app.register_blueprint(dashboard_bp)
        print("Dashboard: Dashboard Blueprint 註冊成功")
        
    except ImportError as e:
        print(f"Dashboard: Dashboard Blueprint 註冊失敗: {e}")
    
    try:
        # 註冊設備設定相關的路由
        from controllers.device_controller import device_bp
        app.register_blueprint(device_bp)
        print("Dashboard: Device Blueprint 註冊成功")
    except ImportError as e:
        print(f"Dashboard: Device Blueprint 註冊失敗: {e}")
        # 如果沒有設備控制器，創建基本的設備設定路由
        register_device_settings_routes()
    
    try:
        # 註冊其他必要的控制器
        from controllers.api_controller import api_bp
        app.register_blueprint(api_bp, url_prefix='/api')
        print("Dashboard: API Blueprint 註冊成功")
    except ImportError as e:
        print(f"Dashboard: API Blueprint 註冊失敗: {e}")

def register_device_settings_routes():
    """註冊基本的設備設定路由（如果沒有專門的控制器）"""
    from flask import request, jsonify, render_template, redirect, url_for, flash
    
    @app.route('/db-setting', methods=['GET', 'POST'])
    def db_setting():
        """設備設定頁面"""
        if request.method == 'POST':
            try:
                if device_settings_manager:
                    # 處理設定儲存
                    settings_data = request.get_json() or request.form.to_dict()
                    device_settings_manager.save_settings(settings_data)
                    return jsonify({'success': True, 'message': '設定已儲存'})
                else:
                    return jsonify({'success': False, 'message': '設備設定管理器未可用'})
            except Exception as e:
                return jsonify({'success': False, 'message': f'儲存設定失敗: {str(e)}'})
        
        # GET 請求 - 顯示設定頁面
        try:
            current_settings = device_settings_manager.load_settings() if device_settings_manager else {}
            return render_template('db_setting.html', settings=current_settings)
        except Exception as e:
            return render_template('error.html', error=f'載入設定頁面失敗: {str(e)}')
    
    @app.route('/api/device-settings', methods=['GET', 'POST'])
    def api_device_settings():
        """API: 獲取或儲存設備設定，支援多設備"""
        if request.method == 'POST':
            try:
                data = request.get_json()
                if not data:
                    return jsonify({'success': False, 'message': '無效的請求資料'})
                
                if device_settings_manager:
                    device_settings_manager.save_settings(data)
                    return jsonify({'success': True, 'message': '設定已儲存'})
                else:
                    return jsonify({'success': False, 'message': '設備設定管理器未可用'})
                    
            except Exception as e:
                return jsonify({'success': False, 'message': f'儲存設定失敗: {str(e)}'})
        else:
            # GET 請求
            try:
                settings = device_settings_manager.load_settings() if device_settings_manager else {}
                return jsonify({'success': True, 'settings': settings})
            except Exception as e:
                return jsonify({'success': False, 'message': f'獲取設定失敗: {str(e)}'})
    
    @app.route('/api/multi-device-settings')
    def api_multi_device_settings():
        """API: 獲取所有設備設定"""
        try:
            if multi_device_settings_manager:
                settings = multi_device_settings_manager.get_all_device_settings()
                return jsonify({'success': True, 'settings': settings})
            else:
                return jsonify({'success': False, 'message': '多設備設定管理器未可用'})
        except Exception as e:
            return jsonify({'success': False, 'message': f'獲取多設備設定失敗: {str(e)}'})

def register_mode_routes():
    """註冊模式相關路由"""
    from flask import jsonify
    
    # 當前模式狀態
    current_mode = {'mode': 'local'}
    
    @app.route('/set-mode', methods=['POST'])
    def set_mode():
        """設定模式"""
        try:
            from flask import request
            data = request.get_json()
            mode = data.get('mode', 'local')
            current_mode['mode'] = mode
            return jsonify({'success': True, 'mode': mode})
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)})
    
    @app.route('/get-mode', methods=['GET'])
    def get_mode():
        """取得當前模式"""
        return jsonify({'mode': current_mode['mode']})

def register_error_handlers():
    """註冊錯誤處理器"""
    from flask import jsonify
    
    @app.errorhandler(404)
    def not_found_error(error):
        """處理404錯誤"""
        return jsonify({
            'success': False,
            'error': 'Not Found',
            'message': '請求的資源不存在'
        }), 404

    @app.errorhandler(500)
    def internal_error(error):
        """處理500錯誤"""
        logging.error(f"內部伺服器錯誤: {error}")
        return jsonify({
            'success': False,
            'error': 'Internal Server Error',
            'message': '內部伺服器錯誤'
        }), 500

def initialize_raspberry_pi_connection():
    """樹莓派連接初始化（已禁用）"""
    print("樹莓派連接功能已移除")

def main():
    """主函數"""
    try:
        print("啟動 Dashboard API 服務...")
        print("支援的路由:")
        print("  - Dashboard 主頁: http://localhost:5001/dashboard")
        print("  - 設備設定: http://localhost:5001/db-setting")
        print("  - API 健康檢查: http://localhost:5001/api/health")
        print("  - API 狀態: http://localhost:5001/api/status")
        
        # 初始化依賴項
        initialize_dependencies()
        
        # 註冊 Blueprint
        register_blueprints()
        
        # 註冊模式路由
        register_mode_routes()
        
        # 註冊錯誤處理器
        register_error_handlers()
        
        # 初始化樹莓派連接
        initialize_raspberry_pi_connection()
        
        # 啟動 Flask 應用程式 (使用不同的端口避免衝突)
        app.run(debug=True, host='0.0.0.0', port=5001)
        
    except Exception as e:
        print(f"啟動 Dashboard API 服務時發生錯誤: {e}")
        print("請檢查:")
        print("1. 端口 5001 是否被其他程式佔用")
        print("2. 相依套件是否已正確安裝")

if __name__ == '__main__':
    main()