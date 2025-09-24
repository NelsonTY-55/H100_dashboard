"""
資料庫控制器
處理資料庫相關的路由
"""

from flask import Blueprint, request, jsonify
import logging
from datetime import datetime
from models import UartDataModel

# 創建 Blueprint
database_bp = Blueprint('database', __name__, url_prefix='/api/database')

# 初始化模型
uart_model = UartDataModel()


@database_bp.route('/factory-areas')
def api_database_factory_areas():
    """獲取工廠區域資訊"""
    try:
        # 模擬工廠區域資料
        factory_areas = [
            {
                'id': 'area_01',
                'name': '生產線 A',
                'description': '主要生產線',
                'device_count': 15,
                'active_devices': 12,
                'status': 'active',
                'floor_level': 1
            },
            {
                'id': 'area_02',
                'name': '生產線 B',
                'description': '輔助生產線',
                'device_count': 8,
                'active_devices': 7,
                'status': 'active',
                'floor_level': 1
            },
            {
                'id': 'area_03',
                'name': '品質檢測區',
                'description': '產品品質檢測',
                'device_count': 5,
                'active_devices': 5,
                'status': 'active',
                'floor_level': 2
            },
            {
                'id': 'area_04',
                'name': '倉儲區',
                'description': '原料與成品倉儲',
                'device_count': 10,
                'active_devices': 8,
                'status': 'maintenance',
                'floor_level': 1
            }
        ]
        
        return jsonify({
            'success': True,
            'data': factory_areas,
            'total_areas': len(factory_areas),
            'total_devices': sum(area['device_count'] for area in factory_areas),
            'active_devices': sum(area['active_devices'] for area in factory_areas)
        })
        
    except Exception as e:
        logging.error(f"獲取工廠區域資訊時發生錯誤: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@database_bp.route('/floor-levels')
def api_database_floor_levels():
    """獲取樓層資訊"""
    try:
        floor_levels = [
            {
                'level': 1,
                'name': '一樓',
                'description': '主要生產區域',
                'area_count': 3,
                'device_count': 33,
                'areas': ['area_01', 'area_02', 'area_04']
            },
            {
                'level': 2,
                'name': '二樓',
                'description': '檢測與辦公區域',
                'area_count': 1,
                'device_count': 5,
                'areas': ['area_03']
            }
        ]
        
        return jsonify({
            'success': True,
            'data': floor_levels,
            'total_floors': len(floor_levels)
        })
        
    except Exception as e:
        logging.error(f"獲取樓層資訊時發生錯誤: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@database_bp.route('/mac-ids')
def api_database_mac_ids():
    """獲取 MAC ID 統計資訊"""
    try:
        mac_ids = uart_model.get_mac_ids()
        
        # 為每個MAC ID添加統計資訊
        mac_stats = []
        for mac_id in mac_ids:
            data_result = uart_model.get_uart_data_from_files(mac_id=mac_id, limit=1000)
            
            if data_result['success']:
                data_count = data_result['total_count']
                channels = uart_model.get_mac_channels(mac_id)
                
                mac_stats.append({
                    'mac_id': mac_id,
                    'data_count': data_count,
                    'channel_count': len(channels),
                    'channels': channels,
                    'last_seen': datetime.now().isoformat(),  # 應該從實際數據獲取
                    'status': 'active' if data_count > 0 else 'inactive'
                })
        
        return jsonify({
            'success': True,
            'data': mac_stats,
            'total_mac_ids': len(mac_stats),
            'active_mac_ids': len([m for m in mac_stats if m['status'] == 'active'])
        })
        
    except Exception as e:
        logging.error(f"獲取MAC ID統計時發生錯誤: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@database_bp.route('/device-models')
def api_database_device_models():
    """獲取設備型號資訊"""
    try:
        device_models = [
            {
                'model': 'H100-TEMP',
                'name': '溫度感測器',
                'description': '高精度溫度感測器',
                'manufacturer': 'SensorTech',
                'version': '2.1',
                'device_count': 15,
                'supported_channels': 4,
                'data_types': ['temperature', 'humidity']
            },
            {
                'model': 'H100-PRESS',
                'name': '壓力感測器',
                'description': '工業級壓力感測器',
                'manufacturer': 'SensorTech',
                'version': '1.5',
                'device_count': 8,
                'supported_channels': 2,
                'data_types': ['pressure', 'flow_rate']
            },
            {
                'model': 'H100-VIBE',
                'name': '震動感測器',
                'description': '機械震動監測感測器',
                'manufacturer': 'SensorTech',
                'version': '3.0',
                'device_count': 12,
                'supported_channels': 6,
                'data_types': ['vibration_x', 'vibration_y', 'vibration_z']
            }
        ]
        
        return jsonify({
            'success': True,
            'data': device_models,
            'total_models': len(device_models),
            'total_devices': sum(model['device_count'] for model in device_models)
        })
        
    except Exception as e:
        logging.error(f"獲取設備型號資訊時發生錯誤: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@database_bp.route('/chart-data')
def api_database_chart_data():
    """獲取資料庫圖表數據"""
    try:
        # 獲取查詢參數
        chart_type = request.args.get('type', 'line')
        time_range = request.args.get('range', '24h')
        mac_id = request.args.get('mac_id')
        
        # 獲取數據
        data_result = uart_model.get_uart_data_from_files(mac_id=mac_id, limit=1000)
        
        if not data_result['success']:
            return jsonify({
                'success': False,
                'error': data_result['error']
            }), 400
        
        # 處理圖表數據
        chart_data = {
            'type': chart_type,
            'time_range': time_range,
            'data_points': [],
            'summary': {
                'total_points': len(data_result['data']),
                'time_span': time_range,
                'data_types': set()
            }
        }
        
        for record in data_result['data']:
            point = {
                'timestamp': record.get('timestamp'),
                'values': {}
            }
            
            # 添加數值型資料
            for key in ['temperature', 'humidity', 'pressure', 'rssi']:
                if key in record and record[key] is not None:
                    try:
                        point['values'][key] = float(record[key])
                        chart_data['summary']['data_types'].add(key)
                    except (ValueError, TypeError):
                        pass
            
            chart_data['data_points'].append(point)
        
        # 轉換 set 為 list 以便 JSON 序列化
        chart_data['summary']['data_types'] = list(chart_data['summary']['data_types'])
        
        return jsonify({
            'success': True,
            'data': chart_data
        })
        
    except Exception as e:
        logging.error(f"獲取圖表數據時發生錯誤: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@database_bp.route('/statistics')
def api_database_statistics():
    """獲取資料庫統計資訊"""
    try:
        # 獲取UART數據統計
        data_result = uart_model.get_uart_data_from_files(limit=50000)
        
        if data_result['success']:
            total_records = data_result['total_count']
            mac_ids = uart_model.get_mac_ids()
            
            statistics = {
                'records': {
                    'total_count': total_records,
                    'today_count': 0,  # 應該從實際數據計算
                    'this_week_count': 0,  # 應該從實際數據計算
                    'this_month_count': 0  # 應該從實際數據計算
                },
                'devices': {
                    'total_mac_ids': len(mac_ids),
                    'active_devices': len(mac_ids),  # 簡化計算
                    'inactive_devices': 0
                },
                'data_quality': {
                    'valid_records': total_records,
                    'invalid_records': 0,
                    'quality_score': 100.0
                },
                'storage': {
                    'database_size': '125 MB',  # 應該從實際檔案獲取
                    'index_size': '15 MB',
                    'free_space': '850 MB'
                }
            }
        else:
            statistics = {
                'records': {'total_count': 0, 'today_count': 0, 'this_week_count': 0, 'this_month_count': 0},
                'devices': {'total_mac_ids': 0, 'active_devices': 0, 'inactive_devices': 0},
                'data_quality': {'valid_records': 0, 'invalid_records': 0, 'quality_score': 0.0},
                'storage': {'database_size': '0 MB', 'index_size': '0 MB', 'free_space': '1 GB'}
            }
        
        return jsonify({
            'success': True,
            'data': statistics,
            'last_updated': datetime.now().isoformat()
        })
        
    except Exception as e:
        logging.error(f"獲取資料庫統計時發生錯誤: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@database_bp.route('/latest-data')
def api_database_latest_data():
    """獲取最新數據"""
    try:
        limit = int(request.args.get('limit', 10))
        mac_id = request.args.get('mac_id')
        
        data_result = uart_model.get_uart_data_from_files(mac_id=mac_id, limit=limit)
        
        return jsonify(data_result)
        
    except Exception as e:
        logging.error(f"獲取最新數據時發生錯誤: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@database_bp.route('/latest-auto')
def api_database_latest_auto():
    """自動獲取最新數據（用於定時更新）"""
    try:
        # 獲取各個MAC ID的最新數據
        mac_ids = uart_model.get_mac_ids()
        latest_data = {}
        
        for mac_id in mac_ids[:5]:  # 限制前5個MAC ID
            data_result = uart_model.get_uart_data_from_files(mac_id=mac_id, limit=1)
            if data_result['success'] and data_result['data']:
                latest_data[mac_id] = data_result['data'][0]
        
        return jsonify({
            'success': True,
            'data': latest_data,
            'update_time': datetime.now().isoformat(),
            'auto_refresh': True
        })
        
    except Exception as e:
        logging.error(f"自動獲取最新數據時發生錯誤: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@database_bp.route('/register-device', methods=['POST'])
def api_database_register_device():
    """註冊新設備到資料庫"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': '沒有接收到設備數據'
            }), 400
        
        # 驗證必要字段
        required_fields = ['mac_id', 'device_model', 'location']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'success': False,
                    'error': f'缺少必要字段: {field}'
                }), 400
        
        # 這裡應該實現實際的設備註冊邏輯
        
        device_info = {
            'mac_id': data['mac_id'],
            'device_model': data['device_model'],
            'location': data['location'],
            'registration_time': datetime.now().isoformat(),
            'status': 'registered',
            'device_id': f"DEV_{data['mac_id'][-6:]}"  # 生成設備ID
        }
        
        return jsonify({
            'success': True,
            'message': '設備註冊成功',
            'data': device_info
        })
        
    except Exception as e:
        logging.error(f"註冊設備時發生錯誤: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@database_bp.route('/device-info')
def api_database_device_info():
    """獲取設備詳細資訊"""
    try:
        mac_id = request.args.get('mac_id')
        device_id = request.args.get('device_id')
        
        if not mac_id and not device_id:
            return jsonify({
                'success': False,
                'error': '需要提供 MAC ID 或設備 ID'
            }), 400
        
        # 這裡應該從實際資料庫獲取設備資訊
        # 暫時返回模擬數據
        
        device_info = {
            'mac_id': mac_id or 'AA:BB:CC:DD:EE:FF',
            'device_id': device_id or f"DEV_{mac_id[-6:] if mac_id else '123456'}",
            'device_model': 'H100-TEMP',
            'device_name': '溫度感測器 #1',
            'location': '生產線 A - 工位 1',
            'installation_date': '2025-01-15',
            'last_maintenance': '2025-08-15',
            'status': 'active',
            'firmware_version': '2.1.0',
            'hardware_version': '1.3',
            'calibration_date': '2025-06-01',
            'warranty_expiry': '2026-01-15'
        }
        
        return jsonify({
            'success': True,
            'data': device_info
        })
        
    except Exception as e:
        logging.error(f"獲取設備資訊時發生錯誤: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500