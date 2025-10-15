"""
模板渲染視圖
處理 HTML 模板渲染和頁面視圖
"""

from flask import render_template, request, session, flash
from typing import Dict, Any, Optional, Tuple
import logging


class TemplateView:
    """模板視圖類"""
    
    @staticmethod
    def render_dashboard(template_name: str, **kwargs) -> str:
        """渲染儀表板模板"""
        try:
            # 添加通用的儀表板上下文
            context = {
                'page_title': '設備監控儀表板',
                'user_session': session.get('user', {}),
                'current_path': request.path,
                'is_mobile': TemplateView._is_mobile_request(),
                **kwargs
            }
            
            return render_template(template_name, **context)
            
        except Exception as e:
            logging.error(f"渲染模板 {template_name} 時發生錯誤: {e}")
            return TemplateView.render_error_page(str(e))
    
    @staticmethod
    def render_error_page(error_message: str, status_code: int = 500) -> str:
        """渲染錯誤頁面"""
        try:
            context = {
                'error_message': error_message,
                'status_code': status_code,
                'page_title': f'錯誤 {status_code}',
                'show_back_button': True
            }
            
            return render_template('error.html', **context)
            
        except Exception as e:
            # 如果連錯誤模板都無法渲染，返回簡單的HTML
            logging.critical(f"無法渲染錯誤模板: {e}")
            return f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>系統錯誤</title>
                <meta charset="utf-8">
            </head>
            <body>
                <h1>系統錯誤</h1>
                <p>{error_message}</p>
                <p>狀態碼: {status_code}</p>
                <a href="javascript:history.back()">返回上頁</a>
            </body>
            </html>
            """
    
    @staticmethod
    def render_404_page() -> str:
        """渲染 404 頁面"""
        try:
            context = {
                'page_title': '頁面不存在',
                'error_message': '您訪問的頁面不存在',
                'status_code': 404,
                'show_home_link': True
            }
            
            return render_template('404.html', **context)
            
        except Exception:
            return TemplateView.render_error_page('頁面不存在', 404)
    
    @staticmethod
    def render_device_page(template_name: str, devices: list = None, **kwargs) -> str:
        """渲染設備相關頁面"""
        try:
            context = {
                'page_title': '設備管理',
                'devices': devices or [],
                'device_count': len(devices) if devices else 0,
                'show_add_device': True,
                **kwargs
            }
            
            return TemplateView.render_dashboard(template_name, **context)
            
        except Exception as e:
            logging.error(f"渲染設備頁面時發生錯誤: {e}")
            return TemplateView.render_error_page(str(e))
    
    @staticmethod
    def render_config_page(template_name: str, config_data: Dict = None, **kwargs) -> str:
        """渲染配置頁面"""
        try:
            context = {
                'page_title': '系統配置',
                'config_data': config_data or {},
                'show_save_button': True,
                'form_id': 'config-form',
                **kwargs
            }
            
            return TemplateView.render_dashboard(template_name, **context)
            
        except Exception as e:
            logging.error(f"渲染配置頁面時發生錯誤: {e}")
            return TemplateView.render_error_page(str(e))
    
    @staticmethod
    def render_data_analysis_page(template_name: str, chart_data: Dict = None, **kwargs) -> str:
        """渲染數據分析頁面"""
        try:
            context = {
                'page_title': '數據分析',
                'chart_data': chart_data or {},
                'enable_charts': True,
                'chart_libraries': ['Chart.js', 'D3.js'],
                **kwargs
            }
            
            return TemplateView.render_dashboard(template_name, **context)
            
        except Exception as e:
            logging.error(f"渲染數據分析頁面時發生錯誤: {e}")
            return TemplateView.render_error_page(str(e))
    
    @staticmethod
    def _is_mobile_request() -> bool:
        """檢查是否為行動裝置請求"""
        user_agent = request.headers.get('User-Agent', '').lower()
        mobile_keywords = ['mobile', 'android', 'iphone', 'ipad', 'ipod', 'blackberry', 'windows phone']
        
        return any(keyword in user_agent for keyword in mobile_keywords)
    
    @staticmethod
    def add_flash_message(message: str, category: str = 'info') -> None:
        """添加 Flash 訊息"""
        flash(message, category)
    
    @staticmethod
    def get_flash_messages():
        """獲取 Flash 訊息"""
        return session.get('_flashes', [])


class FormView:
    """表單視圖類"""
    
    @staticmethod
    def validate_device_form(form_data: Dict) -> Tuple[bool, list]:
        """驗證設備表單"""
        errors = []
        
        # 檢查必要字段
        required_fields = ['device_id', 'device_name', 'device_type']
        for field in required_fields:
            if not form_data.get(field):
                errors.append(f'{field} 為必填字段')
        
        # 檢查設備ID格式
        device_id = form_data.get('device_id', '')
        if device_id and not device_id.replace('_', '').replace('-', '').isalnum():
            errors.append('設備ID只能包含字母、數字、下劃線和連字符')
        
        # 檢查設備名稱長度
        device_name = form_data.get('device_name', '')
        if device_name and len(device_name) > 100:
            errors.append('設備名稱不能超過100個字符')
        
        return len(errors) == 0, errors
    
    @staticmethod
    def validate_config_form(form_data: Dict) -> Tuple[bool, list]:
        """驗證配置表單"""
        errors = []
        
        # 檢查端口號
        port = form_data.get('port')
        if port:
            try:
                port_num = int(port)
                if port_num < 1 or port_num > 65535:
                    errors.append('端口號必須在 1-65535 之間')
            except ValueError:
                errors.append('端口號必須是數字')
        
        # 檢查主機地址
        host = form_data.get('host', '')
        if host and len(host) > 255:
            errors.append('主機地址不能超過255個字符')
        
        # 檢查超時設定
        timeout = form_data.get('timeout')
        if timeout:
            try:
                timeout_num = int(timeout)
                if timeout_num < 1 or timeout_num > 300:
                    errors.append('超時時間必須在 1-300 秒之間')
            except ValueError:
                errors.append('超時時間必須是數字')
        
        return len(errors) == 0, errors
    
    @staticmethod
    def validate_wifi_form(form_data: Dict) -> Tuple[bool, list]:
        """驗證WiFi表單"""
        errors = []
        
        # 檢查SSID
        ssid = form_data.get('ssid', '')
        if not ssid:
            errors.append('SSID 為必填字段')
        elif len(ssid) > 32:
            errors.append('SSID 不能超過32個字符')
        
        # 檢查密碼
        password = form_data.get('password', '')
        if password and len(password) < 8:
            errors.append('WiFi密碼至少需要8個字符')
        
        return len(errors) == 0, errors