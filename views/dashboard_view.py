"""
Dashboard 視圖
處理 Dashboard 相關的回應格式化和模板渲染
"""

from flask import jsonify, render_template
from datetime import datetime
from typing import Any, Dict, Optional
import logging


class DashboardView:
    """Dashboard 視圖類"""
    
    @staticmethod
    def render_dashboard(system_info: Dict, app_stats: Dict, device_settings: Dict, 
                        raspberry_pi_config: Dict = None, pi_status: Dict = None) -> str:
        """渲染 Dashboard 主頁面"""
        try:
            return render_template(
                'dashboard.html',
                system_info=system_info,
                app_stats=app_stats,
                device_settings=device_settings,
                raspberry_pi_config=raspberry_pi_config or {'host': '本地主機', 'port': 5001},
                pi_status=pi_status or {'connected': False}
            )
        except Exception as e:
            logging.error(f"渲染 Dashboard 頁面失敗: {e}")
            return render_template('error.html', error=str(e))
    
    @staticmethod
    def render_data_analysis() -> str:
        """渲染資料分析頁面"""
        try:
            return render_template('data_analysis.html')
        except Exception as e:
            logging.error(f"渲染資料分析頁面失敗: {e}")
            return render_template('error.html', error=str(e))
    
    @staticmethod
    def render_dashboard_11() -> str:
        """渲染儀表板總覽頁面 (11.html)"""
        try:
            return render_template('11.html')
        except Exception as e:
            logging.error(f"渲染儀表板總覽頁面失敗: {e}")
            return render_template('error.html', error=str(e))
    
    @staticmethod
    def render_error(error_message: str, status_code: int = 500) -> tuple:
        """渲染錯誤頁面"""
        try:
            return render_template('error.html', error=error_message), status_code
        except Exception as e:
            # 如果連錯誤頁面都無法渲染，返回基本 HTML
            html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>錯誤</title>
                <meta charset="utf-8">
            </head>
            <body>
                <h1>系統錯誤</h1>
                <p>原始錯誤: {error_message}</p>
                <p>渲染錯誤: {str(e)}</p>
            </body>
            </html>
            """
            return html, status_code


class DashboardApiView:
    """Dashboard API 視圖類"""
    
    @staticmethod
    def success_response(data: Any = None, message: str = None, 
                        extra_fields: Dict = None) -> Dict:
        """標準成功回應"""
        response = {
            'success': True,
            'timestamp': datetime.now().isoformat()
        }
        
        if data is not None:
            response['data'] = data
        
        if message:
            response['message'] = message
        
        if extra_fields:
            response.update(extra_fields)
        
        return jsonify(response)
    
    @staticmethod
    def error_response(message: str, status_code: int = 400, 
                      error_type: str = None, details: Dict = None) -> tuple:
        """標準錯誤回應"""
        response = {
            'success': False,
            'message': message,
            'timestamp': datetime.now().isoformat()
        }
        
        if error_type:
            response['error_type'] = error_type
        
        if details:
            response['details'] = details
        
        return jsonify(response), status_code
    
    @staticmethod
    def health_response(service_name: str = "Dashboard API", 
                       system_info: Dict = None) -> Dict:
        """健康檢查回應"""
        response = {
            'status': 'healthy',
            'service': service_name,
            'timestamp': datetime.now().isoformat()
        }
        
        if system_info:
            response['system_info'] = system_info
        
        return jsonify(response)
    
    @staticmethod
    def status_response(service_name: str = "Dashboard API", version: str = "1.0.0",
                       uptime: str = None, additional_status: Dict = None) -> Dict:
        """服務狀態回應"""
        response = {
            'success': True,
            'service': service_name,
            'version': version,
            'uptime': uptime or datetime.now().isoformat()
        }
        
        if additional_status:
            response.update(additional_status)
        
        return jsonify(response)
    
    @staticmethod
    def chart_data_response(data, total_channels: int = 0, 
                           source: str = "本地主機", mac_filter: str = None,
                           data_source: str = None) -> Dict:
        """圖表數據回應"""
        response = {
            'success': True,
            'data': data,
            'total_channels': total_channels,
            'source': source,
            'raspberry_pi_ip': source,
            'timestamp': datetime.now().isoformat()
        }
        
        if mac_filter:
            response['filtered_by_mac_id'] = mac_filter
        
        if data_source:
            response['data_source'] = data_source
        
        return jsonify(response)
    
    @staticmethod
    def stats_response(system_stats: Dict, app_stats: Dict, 
                      device_settings: Dict, connection_status: str = "本地模式") -> Dict:
        """統計資料回應"""
        return jsonify({
            'success': True,
            'system': system_stats,
            'application': app_stats,
            'device_settings': device_settings,
            'timestamp': datetime.now().isoformat(),
            'source': '本地',
            'connection_status': connection_status
        })
    
    @staticmethod
    def device_settings_response(device_settings: Dict, multi_device_settings: Dict,
                                is_configured: bool) -> Dict:
        """設備設定回應"""
        return jsonify({
            'success': True,
            'device_settings': device_settings,
            'multi_device_settings': multi_device_settings,
            'is_configured': is_configured,
            'timestamp': datetime.now().isoformat()
        })
    
    @staticmethod
    def devices_list_response(devices, count: int = None) -> Dict:
        """設備列表回應"""
        return jsonify({
            'success': True,
            'devices': devices,
            'count': count if count is not None else len(devices),
            'timestamp': datetime.now().isoformat()
        })
    
    @staticmethod
    def areas_response(areas, locations, models, 
                      device_count: int) -> Dict:
        """區域統計回應"""
        return jsonify({
            'success': True,
            'areas': sorted(areas),
            'locations': sorted(locations),
            'models': sorted(models),
            'device_count': device_count,
            'timestamp': datetime.now().isoformat()
        })
    
    @staticmethod
    def overview_response(overview_data: Dict) -> Dict:
        """總覽資料回應"""
        response = {
            'success': True,
            'overview': overview_data,
            'timestamp': datetime.now().isoformat()
        }
        return jsonify(response)
    
    @staticmethod
    def uart_status_response(status: str, is_running: bool = False, 
                            data_count: int = 0, additional_info: Dict = None) -> Dict:
        """UART 狀態回應"""
        response = {
            'success': True,
            'status': status,
            'is_running': is_running,
            'data_count': data_count,
            'last_update': datetime.now().isoformat()
        }
        
        if additional_info:
            response.update(additional_info)
        
        return jsonify(response)
    
    @staticmethod
    def mac_ids_response(mac_ids) -> Dict:
        """MAC ID 列表回應"""
        return jsonify({
            'success': True,
            'mac_ids': sorted(mac_ids),
            'count': len(mac_ids)
        })
    
    @staticmethod
    def mac_channels_response(data: Dict, mac_id: str = None) -> Dict:
        """MAC 通道資訊回應"""
        response = {
            'success': True,
            'data': data
        }
        
        if mac_id:
            response['mac_id'] = mac_id
            if isinstance(data, dict) and 'channels' in data:
                response['channel_count'] = len(data.get('channels', {}))
        elif isinstance(data, dict):
            response['mac_count'] = len(data)
        
        return jsonify(response)
    
    @staticmethod
    def mac_data_response(mac_id: str, data, minutes: int = 10) -> Dict:
        """MAC 數據回應"""
        return jsonify({
            'success': True,
            'mac_id': mac_id,
            'minutes': minutes,
            'data': data,
            'count': len(data),
            'timestamp': datetime.now().isoformat()
        })
    
    @staticmethod
    def database_response(data: Any, query_params: Dict = None, 
                         count: int = None) -> Dict:
        """資料庫查詢回應"""
        response = {
            'success': True,
            'data': data,
            'timestamp': datetime.now().isoformat()
        }
        
        if count is not None:
            response['count'] = count
        elif isinstance(data, list):
            response['count'] = len(data)
        
        if query_params:
            response['query_params'] = query_params
        
        return jsonify(response)
    
    @staticmethod
    def device_registration_response(success: bool, message: str, 
                                   device_id: str = None) -> Dict:
        """設備註冊回應"""
        response = {
            'success': success,
            'message': message,
            'timestamp': datetime.now().isoformat()
        }
        
        if device_id:
            response['device_id'] = device_id
        
        return jsonify(response)


class DashboardErrorView:
    """Dashboard 錯誤視圖"""
    
    @staticmethod
    def not_found_error() -> tuple:
        """404 錯誤"""
        return jsonify({
            'success': False,
            'error': 'Not Found',
            'message': '請求的資源不存在',
            'timestamp': datetime.now().isoformat()
        }), 404
    
    @staticmethod
    def internal_error(error_message: str = '內部伺服器錯誤') -> tuple:
        """500 錯誤"""
        return jsonify({
            'success': False,
            'error': 'Internal Server Error',
            'message': error_message,
            'timestamp': datetime.now().isoformat()
        }), 500
    
    @staticmethod
    def service_unavailable(service_name: str = '服務') -> tuple:
        """503 錯誤 - 服務不可用"""
        return jsonify({
            'success': False,
            'error': 'Service Unavailable',
            'message': f'{service_name}暫時無法使用',
            'timestamp': datetime.now().isoformat()
        }), 503
    
    @staticmethod
    def validation_error(message: str = '驗證失敗', details: Dict = None) -> tuple:
        """422 錯誤 - 驗證失敗"""
        response = {
            'success': False,
            'error': 'Validation Error',
            'message': message,
            'timestamp': datetime.now().isoformat()
        }
        
        if details:
            response['details'] = details
        
        return jsonify(response), 422
    
    @staticmethod
    def unauthorized_error(message: str = '未授權存取') -> tuple:
        """401 錯誤 - 未授權"""
        return jsonify({
            'success': False,
            'error': 'Unauthorized',
            'message': message,
            'timestamp': datetime.now().isoformat()
        }), 401
    
    @staticmethod
    def forbidden_error(message: str = '禁止存取') -> tuple:
        """403 錯誤 - 禁止存取"""
        return jsonify({
            'success': False,
            'error': 'Forbidden',
            'message': message,
            'timestamp': datetime.now().isoformat()
        }), 403