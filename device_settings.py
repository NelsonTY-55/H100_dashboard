# Device Settings Manager
# 設備設定管理模組

import json
import os
from datetime import datetime

class DeviceSettingsManager:
    def __init__(self, config_file='device_settings.json'):
        """
        初始化設備設定管理器
        
        Args:
            config_file (str): 設定檔案路徑
        """
        # 使用絕對路徑確保設定檔案在正確位置
        if not os.path.isabs(config_file):
            # 如果是相對路徑，將其放在腳本目錄下
            script_dir = os.path.dirname(os.path.abspath(__file__))
            self.config_file = os.path.join(script_dir, config_file)
        else:
            self.config_file = config_file
        self.default_settings = {
            'device_name': '',
            'device_location': '',
            'device_model': {
                '0': '',
                '1': '',
                '2': '',
                '3': '',
                '4': '',
                '5': '',
                '6': ''
            },
            'device_serial': '',
            'device_description': '',
            'created_at': None,
            'updated_at': None
        }
        
    def load_settings(self):
        """
        載入設備設定
        
        Returns:
            dict: 設備設定字典
        """
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                    
                    # 處理舊版本的 device_model 格式相容性
                    if isinstance(settings.get('device_model'), str):
                        old_model = settings['device_model']
                        settings['device_model'] = {
                            '0': old_model,
                            '1': '',
                            '2': '',
                            '3': '',
                            '4': '',
                            '5': '',
                            '6': ''
                        }
                    elif not isinstance(settings.get('device_model'), dict):
                        settings['device_model'] = self.default_settings['device_model'].copy()
                    
                    # 確保所有必要的欄位都存在
                    for key, value in self.default_settings.items():
                        if key not in settings:
                            settings[key] = value
                    return settings
            else:
                return self.default_settings.copy()
        except Exception as e:
            print(f"載入設備設定時發生錯誤: {e}")
            return self.default_settings.copy()
    
    def save_settings(self, settings):
        """
        儲存設備設定
        
        Args:
            settings (dict): 要儲存的設定字典
            
        Returns:
            bool: 儲存是否成功
        """
        try:
            # 添加時間戳記
            current_time = datetime.now().isoformat()
            existing_settings = self.load_settings()
            
            # 如果是第一次建立，設定 created_at
            if not existing_settings.get('created_at'):
                settings['created_at'] = current_time
            else:
                settings['created_at'] = existing_settings['created_at']
            
            settings['updated_at'] = current_time
            
            # 儲存到檔案
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(settings, f, ensure_ascii=False, indent=2)
            
            print(f"設備設定已儲存到 {self.config_file}")
            return True
            
        except Exception as e:
            print(f"儲存設備設定時發生錯誤: {e}")
            return False
    
    def get_device_name(self):
        """
        取得設備名稱
        
        Returns:
            str: 設備名稱
        """
        settings = self.load_settings()
        return settings.get('device_name', '')
    
    def get_device_info(self):
        """
        取得完整設備資訊
        
        Returns:
            dict: 設備資訊字典
        """
        return self.load_settings()
    
    def is_configured(self):
        """
        檢查是否已完成基本設定
        
        Returns:
            bool: 是否已設定設備名稱
        """
        settings = self.load_settings()
        return bool(settings.get('device_name', '').strip())
    
    def reset_settings(self):
        """
        重設所有設定
        
        Returns:
            bool: 重設是否成功
        """
        try:
            if os.path.exists(self.config_file):
                os.remove(self.config_file)
            return True
        except Exception as e:
            print(f"重設設定時發生錯誤: {e}")
            return False

# 建立全域實例
device_settings_manager = DeviceSettingsManager()

# 以下是 Flask 路由的範例程式碼，請加入到您的主要 Flask 應用程式中

"""
# 在您的 Flask 應用程式中加入以下路由

from flask import Flask, render_template, request, jsonify, redirect, url_for
from device_settings import device_settings_manager

@app.route('/db-setting')
def db_setting():
    # 顯示 DB 設定頁面
    return render_template('db_setting.html')

@app.route('/api/device/settings', methods=['GET', 'POST'])
def api_device_settings():
    if request.method == 'GET':
        # 取得目前的設備設定
        settings = device_settings_manager.get_device_info()
        return jsonify({
            'success': True,
            'settings': settings
        })
    
    elif request.method == 'POST':
        # 儲存設備設定
        try:
            data = request.get_json()
            
            # 驗證必要欄位
            if not data.get('device_name', '').strip():
                return jsonify({
                    'success': False,  
                    'message': '設備名稱為必填欄位'
                }), 400
            
            # 儲存設定
            success = device_settings_manager.save_settings(data)
            
            if success:
                return jsonify({
                    'success': True,
                    'message': '設定儲存成功'
                })
            else:
                return jsonify({
                    'success': False,
                    'message': '設定儲存失敗'
                }), 500
                
        except Exception as e:
            return jsonify({
                'success': False,
                'message': f'伺服器錯誤: {str(e)}'
            }), 500

@app.route('/dashboard')
def dashboard():
    # 檢查是否已完成設備設定
    if not device_settings_manager.is_configured():
        return redirect(url_for('db_setting'))
    
    # 取得設備設定並傳遞給模板
    device_settings = device_settings_manager.get_device_info()
    
    # 這裡加入其他必要的資料（app_stats 等）
    app_stats = {
        'uart_running': False,  # 請根據實際狀況設定
        'uart_data_count': 0,
        'current_mode': 'idle',
        'supported_protocols': []
    }
    
    return render_template('dashboard.html', 
                         device_settings=device_settings,
                         app_stats=app_stats)

# 在應用程式啟動時檢查設定
@app.before_first_request
def check_device_settings():
    if not device_settings_manager.is_configured():
        print("警告: 尚未完成設備設定，請先訪問 /db-setting 頁面進行設定")

"""
