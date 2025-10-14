"""
Dashboard API 視圖
處理 Dashboard API 的回應格式和數據展示
"""

from flask import jsonify
from datetime import datetime
from typing import Any, Dict, Optional
import logging


class DashboardAPIView:
    """Dashboard API 視圖類"""
    
    @staticmethod
    def success_response(data: Any = None, message: str = None, status_code: int = 200) -> tuple:
        """成功回應格式"""
        response = {
            'success': True,
            'timestamp': datetime.now().isoformat()
        }
        
        if data is not None:
            response['data'] = data
        
        if message:
            response['message'] = message
        
        return jsonify(response), status_code
    
    @staticmethod
    def error_response(error: str, status_code: int = 500, error_code: str = None) -> tuple:
        """錯誤回應格式"""
        response = {
            'success': False,
            'error': error,
            'timestamp': datetime.now().isoformat()
        }
        
        if error_code:
            response['error_code'] = error_code
        
        if status_code != 500:
            response['status_code'] = status_code
        
        return jsonify(response), status_code
    
    @staticmethod
    def health_response(status: str = 'healthy', uptime: str = None, additional_info: Dict = None) -> Dict:
        """健康檢查回應格式"""
        response = {
            'status': status,
            'service': 'dashboard-api',
            'timestamp': datetime.now().isoformat()
        }
        
        if uptime:
            response['uptime'] = uptime
        
        if additional_info:
            response.update(additional_info)
        
        return response
    
    @staticmethod
    def system_info_response(system_data: Dict) -> Dict:
        """系統資訊回應格式"""
        return {
            'success': True,
            'data': system_data,
            'data_type': 'system_info',
            'timestamp': datetime.now().isoformat()
        }
    
    @staticmethod
    def dashboard_data_response(dashboard_data: Dict) -> Dict:
        """儀表板資料回應格式"""
        return {
            'success': True,
            'data': dashboard_data,
            'data_type': 'dashboard_data',
            'timestamp': datetime.now().isoformat()
        }
    
    @staticmethod
    def config_response(config_data: Dict) -> Dict:
        """設定資訊回應格式"""
        return {
            'success': True,
            'data': config_data,
            'data_type': 'config',
            'timestamp': datetime.now().isoformat()
        }
    
    @staticmethod
    def status_response(status_data: Dict) -> Dict:
        """服務狀態回應格式"""
        return {
            'success': True,
            'data': status_data,
            'data_type': 'service_status',
            'timestamp': datetime.now().isoformat()
        }
    
    @staticmethod
    def api_info_response() -> Dict:
        """API 資訊回應格式"""
        return {
            'service': 'H100 Dashboard API',
            'version': '1.0.0',
            'status': 'running',
            'architecture': 'MVC',
            'endpoints': {
                'health': '/api/health',
                'system': '/api/system',
                'dashboard': '/api/dashboard',
                'config': '/api/config',
                'status': '/api/status'
            },
            'documentation': {
                'swagger': '/api/docs',
                'readme': '/api/readme'
            },
            'timestamp': datetime.now().isoformat()
        }
    
    @staticmethod
    def format_bytes(bytes_value: int) -> Dict[str, Any]:
        """格式化位元組數值"""
        units = ['B', 'KB', 'MB', 'GB', 'TB']
        size = bytes_value
        unit_index = 0
        
        while size >= 1024 and unit_index < len(units) - 1:
            size /= 1024
            unit_index += 1
        
        return {
            'raw': bytes_value,
            'formatted': f"{size:.2f} {units[unit_index]}",
            'value': round(size, 2),
            'unit': units[unit_index]
        }
    
    @staticmethod
    def format_percentage(value: float) -> Dict[str, Any]:
        """格式化百分比數值"""
        return {
            'raw': value,
            'formatted': f"{value:.1f}%",
            'value': round(value, 1),
            'unit': '%'
        }
    
    @staticmethod
    def format_system_info(system_data: Dict) -> Dict:
        """格式化系統資訊回應"""
        formatted_data = system_data.copy()
        
        # 格式化記憶體資訊
        if 'memory' in formatted_data and isinstance(formatted_data['memory'], dict):
            memory = formatted_data['memory']
            for key in ['total', 'available', 'used']:
                if key in memory:
                    memory[f'{key}_formatted'] = DashboardAPIView.format_bytes(memory[key])
            
            if 'percent' in memory:
                memory['percent_formatted'] = DashboardAPIView.format_percentage(memory['percent'])
        
        # 格式化磁碟資訊
        if 'disk' in formatted_data and isinstance(formatted_data['disk'], dict):
            disk = formatted_data['disk']
            for key in ['total', 'used', 'free']:
                if key in disk:
                    disk[f'{key}_formatted'] = DashboardAPIView.format_bytes(disk[key])
            
            if 'percent' in disk:
                disk['percent_formatted'] = DashboardAPIView.format_percentage(disk['percent'])
        
        return formatted_data
    
    @staticmethod
    def format_performance_data(performance_data: Dict) -> Dict:
        """格式化效能資料回應"""
        formatted_data = performance_data.copy()
        
        # 格式化 CPU 使用率
        if 'cpu_percent' in formatted_data:
            formatted_data['cpu_percent_formatted'] = DashboardAPIView.format_percentage(formatted_data['cpu_percent'])
        
        # 格式化記憶體使用率
        if 'memory_percent' in formatted_data:
            formatted_data['memory_percent_formatted'] = DashboardAPIView.format_percentage(formatted_data['memory_percent'])
        
        # 格式化磁碟 I/O
        if 'disk_io' in formatted_data and isinstance(formatted_data['disk_io'], dict):
            disk_io = formatted_data['disk_io']
            for key in ['read_bytes', 'write_bytes']:
                if key in disk_io:
                    disk_io[f'{key}_formatted'] = DashboardAPIView.format_bytes(disk_io[key])
        
        # 格式化網路 I/O
        if 'network_io' in formatted_data and isinstance(formatted_data['network_io'], dict):
            network_io = formatted_data['network_io']
            for key in ['bytes_sent', 'bytes_recv']:
                if key in network_io:
                    network_io[f'{key}_formatted'] = DashboardAPIView.format_bytes(network_io[key])
        
        return formatted_data


class DashboardAPIErrorView:
    """Dashboard API 錯誤視圖類"""
    
    @staticmethod
    def not_found_error() -> tuple:
        """404 錯誤回應"""
        return DashboardAPIView.error_response(
            error='API 端點不存在',
            status_code=404,
            error_code='NOT_FOUND'
        )
    
    @staticmethod
    def internal_server_error() -> tuple:
        """500 錯誤回應"""
        return DashboardAPIView.error_response(
            error='內部伺服器錯誤',
            status_code=500,
            error_code='INTERNAL_SERVER_ERROR'
        )
    
    @staticmethod
    def method_not_allowed_error() -> tuple:
        """405 錯誤回應"""
        return DashboardAPIView.error_response(
            error='不允許的請求方法',
            status_code=405,
            error_code='METHOD_NOT_ALLOWED'
        )
    
    @staticmethod
    def service_unavailable_error() -> tuple:
        """503 錯誤回應"""
        return DashboardAPIView.error_response(
            error='服務暫時無法使用',
            status_code=503,
            error_code='SERVICE_UNAVAILABLE'
        )