"""
API 回應視圖
標準化 API 回應格式
"""

from flask import jsonify
from datetime import datetime
from typing import Any, Dict, Optional, List
import logging


class ApiResponseView:
    """API 回應視圖類"""
    
    @staticmethod
    def success(data: Any = None, message: str = None, status_code: int = 200) -> tuple:
        """成功回應"""
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
    def error(error: str, status_code: int = 400, details: Dict = None) -> tuple:
        """錯誤回應"""
        response = {
            'success': False,
            'error': error,
            'timestamp': datetime.now().isoformat()
        }
        
        if details:
            response['details'] = details
        
        return jsonify(response), status_code
    
    @staticmethod
    def validation_error(errors: List[str], status_code: int = 422) -> tuple:
        """驗證錯誤回應"""
        return ApiResponseView.error(
            error='驗證失敗',
            status_code=status_code,
            details={'validation_errors': errors}
        )
    
    @staticmethod
    def not_found(resource: str = '資源') -> tuple:
        """404 回應"""
        return ApiResponseView.error(
            error=f'{resource}不存在',
            status_code=404
        )
    
    @staticmethod
    def unauthorized(message: str = '未授權訪問') -> tuple:
        """401 回應"""
        return ApiResponseView.error(
            error=message,
            status_code=401
        )
    
    @staticmethod
    def forbidden(message: str = '禁止訪問') -> tuple:
        """403 回應"""
        return ApiResponseView.error(
            error=message,
            status_code=403
        )
    
    @staticmethod
    def internal_error(error: Exception = None) -> tuple:
        """500 回應"""
        error_message = '內部伺服器錯誤'
        
        if error:
            logging.error(f"內部伺服器錯誤: {error}")
            error_message = str(error)
        
        return ApiResponseView.error(
            error=error_message,
            status_code=500
        )
    
    @staticmethod
    def paginated(data: List[Any], page: int, per_page: int, total: int, **kwargs) -> tuple:
        """分頁回應"""
        total_pages = (total + per_page - 1) // per_page  # 向上取整
        
        response_data = {
            'items': data,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total,
                'total_pages': total_pages,
                'has_next': page < total_pages,
                'has_prev': page > 1
            }
        }
        
        # 添加其他自定義資料
        response_data.update(kwargs)
        
        return ApiResponseView.success(response_data)


class DataResponseView:
    """資料回應視圖類"""
    
    @staticmethod
    def uart_data(data: List[Dict], total_count: int, **kwargs) -> tuple:
        """UART 資料回應格式"""
        response_data = {
            'records': data,
            'total_count': total_count,
            'record_count': len(data)
        }
        
        # 添加其他資訊
        response_data.update(kwargs)
        
        return ApiResponseView.success(response_data)
    
    @staticmethod
    def device_list(devices: List[Dict], **kwargs) -> tuple:
        """設備列表回應格式"""
        response_data = {
            'devices': devices,
            'device_count': len(devices)
        }
        
        # 添加其他資訊
        response_data.update(kwargs)
        
        return ApiResponseView.success(response_data)
    
    @staticmethod
    def system_status(status_data: Dict, **kwargs) -> tuple:
        """系統狀態回應格式"""
        response_data = {
            'status': status_data,
            'check_time': datetime.now().isoformat()
        }
        
        response_data.update(kwargs)
        
        return ApiResponseView.success(response_data)
    
    @staticmethod
    def network_status(network_data: Dict, **kwargs) -> tuple:
        """網路狀態回應格式"""
        response_data = {
            'network': network_data,
            'test_time': datetime.now().isoformat()
        }
        
        response_data.update(kwargs)
        
        return ApiResponseView.success(response_data)


class ChartResponseView:
    """圖表資料回應視圖類"""
    
    @staticmethod
    def time_series(data: List[Dict], x_field: str = 'timestamp', y_fields: List[str] = None) -> tuple:
        """時間序列圖表回應"""
        if y_fields is None:
            y_fields = ['value']
        
        # 整理圖表數據
        chart_data = {
            'type': 'time_series',
            'x_axis': x_field,
            'y_axes': y_fields,
            'data_points': data,
            'data_count': len(data)
        }
        
        return ApiResponseView.success(chart_data)
    
    @staticmethod
    def bar_chart(data: List[Dict], x_field: str, y_field: str, **kwargs) -> tuple:
        """長條圖回應"""
        chart_data = {
            'type': 'bar_chart',
            'x_axis': x_field,
            'y_axis': y_field,
            'data_points': data,
            'data_count': len(data)
        }
        
        chart_data.update(kwargs)
        
        return ApiResponseView.success(chart_data)
    
    @staticmethod
    def pie_chart(data: List[Dict], label_field: str, value_field: str, **kwargs) -> tuple:
        """圓餅圖回應"""
        chart_data = {
            'type': 'pie_chart',
            'label_field': label_field,
            'value_field': value_field,
            'data_points': data,
            'data_count': len(data)
        }
        
        chart_data.update(kwargs)
        
        return ApiResponseView.success(chart_data)