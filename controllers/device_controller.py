"""
設備控制器
處理設備設定和管理相關的路由
"""

from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
import logging
from models import DeviceSettingsModel

# 創建 Blueprint
device_bp = Blueprint('device', __name__)

# 初始化模型
device_model = DeviceSettingsModel()


@device_bp.route('/db-setting')
def db_setting():
    """設備設定頁面"""
    try:
        device_settings = device_model.load_device_settings()
        multi_device_settings = device_model.load_multi_device_settings()
        
        return render_template('db_setting.html',
                             device_settings=device_settings.get('data', {}),
                             multi_device_settings=multi_device_settings.get('data', {}))
    except Exception as e:
        logging.error(f"載入設備設定頁面時發生錯誤: {e}")
        return render_template('error.html', error=str(e)), 500


@device_bp.route('/api/device-settings', methods=['GET', 'POST'])
def api_device_settings():
    """設備設定 API"""
    try:
        if request.method == 'GET':
            # 獲取設備設定
            device_settings = device_model.load_device_settings()
            return jsonify(device_settings)
        
        elif request.method == 'POST':
            # 儲存設備設定
            data = request.get_json()
            if not data:
                return jsonify({
                    'success': False,
                    'error': '沒有接收到設定資料'
                }), 400
            
            result = device_model.save_device_settings(data)
            
            if result['success']:
                return jsonify(result)
            else:
                return jsonify(result), 500
                
    except Exception as e:
        logging.error(f"處理設備設定 API 時發生錯誤: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@device_bp.route('/api/multi-device-settings', methods=['GET', 'POST'])
def api_multi_device_settings():
    """多設備設定 API"""
    try:
        if request.method == 'GET':
            # 獲取多設備設定
            multi_device_settings = device_model.load_multi_device_settings()
            return jsonify(multi_device_settings)
        
        elif request.method == 'POST':
            # 儲存多設備設定
            data = request.get_json()
            if not data:
                return jsonify({
                    'success': False,
                    'error': '沒有接收到設定資料'
                }), 400
            
            result = device_model.save_multi_device_settings(data)
            
            if result['success']:
                return jsonify(result)
            else:
                return jsonify(result), 500
                
    except Exception as e:
        logging.error(f"處理多設備設定 API 時發生錯誤: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@device_bp.route('/api/device/<device_id>', methods=['GET', 'PUT', 'DELETE'])
def api_device_management(device_id):
    """設備管理 API"""
    try:
        if request.method == 'GET':
            # 獲取指定設備資訊
            device = device_model.get_device_by_id(device_id)
            if device:
                return jsonify({
                    'success': True,
                    'data': device
                })
            else:
                return jsonify({
                    'success': False,
                    'error': f'找不到設備 ID: {device_id}'
                }), 404
        
        elif request.method == 'PUT':
            # 更新設備設定
            data = request.get_json()
            if not data:
                return jsonify({
                    'success': False,
                    'error': '沒有接收到更新資料'
                }), 400
            
            result = device_model.update_device_settings(device_id, data)
            
            if result['success']:
                return jsonify(result)
            else:
                return jsonify(result), 400 if '找不到設備' in result.get('error', '') else 500
        
        elif request.method == 'DELETE':
            # 刪除設備
            result = device_model.remove_device(device_id)
            
            if result['success']:
                return jsonify(result)
            else:
                return jsonify(result), 400 if '找不到設備' in result.get('error', '') else 500
                
    except Exception as e:
        logging.error(f"處理設備管理 API 時發生錯誤: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@device_bp.route('/api/devices', methods=['GET', 'POST'])
def api_devices():
    """設備列表 API"""
    try:
        if request.method == 'GET':
            # 獲取所有設備
            devices = device_model.get_all_devices()
            return jsonify({
                'success': True,
                'data': devices,
                'total_count': len(devices)
            })
        
        elif request.method == 'POST':
            # 新增設備
            data = request.get_json()
            if not data:
                return jsonify({
                    'success': False,
                    'error': '沒有接收到設備資料'
                }), 400
            
            # 驗證必要字段
            if 'id' not in data:
                return jsonify({
                    'success': False,
                    'error': '缺少設備 ID'
                }), 400
            
            result = device_model.add_device(data)
            
            if result['success']:
                return jsonify(result), 201
            else:
                return jsonify(result), 400 if '已存在' in result.get('error', '') else 500
                
    except Exception as e:
        logging.error(f"處理設備列表 API 時發生錯誤: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@device_bp.route('/api/devices/search')
def api_devices_search():
    """設備搜尋 API"""
    try:
        query = request.args.get('q', '').strip()
        device_type = request.args.get('type', '')
        status = request.args.get('status', '')
        
        devices = device_model.get_all_devices()
        
        # 過濾設備
        filtered_devices = []
        for device in devices:
            # 名稱搜尋
            if query and query.lower() not in device.get('name', '').lower():
                continue
            
            # 類型過濾
            if device_type and device.get('type', '') != device_type:
                continue
            
            # 狀態過濾
            if status and device.get('status', '') != status:
                continue
            
            filtered_devices.append(device)
        
        return jsonify({
            'success': True,
            'data': filtered_devices,
            'total_count': len(filtered_devices),
            'query': query,
            'filters': {
                'type': device_type,
                'status': status
            }
        })
        
    except Exception as e:
        logging.error(f"搜尋設備時發生錯誤: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500