# controllers/integrated_device_controller.py
from flask import Blueprint, render_template, request, jsonify, url_for
import logging
from datetime import datetime

# 創建 Blueprint
integrated_device_bp = Blueprint('integrated_device', __name__)


@integrated_device_bp.route('/db-setting')
def db_setting():
    """設備設定頁面"""
    logging.info(f'訪問設備設定頁面, remote_addr={request.remote_addr}')
    
    # 檢查是否從 dashboard 重定向過來
    redirect_to_dashboard = request.args.get('redirect', 'false').lower() == 'true'
    
    # 載入當前設備設定
    try:
        from device_settings import device_settings_manager
        current_settings = device_settings_manager.load_settings()
    except Exception as e:
        logging.error(f"載入設備設定時發生錯誤: {e}")
        from device_settings import device_settings_manager
        current_settings = device_settings_manager.default_settings.copy()
    
    return render_template('db_setting.html', 
                         current_settings=current_settings,
                         redirect_to_dashboard=redirect_to_dashboard)


@integrated_device_bp.route('/api/device-settings', methods=['GET', 'POST'])
def api_device_settings():
    """API: 獲取或儲存設備設定，支援多設備"""
    from device_settings import device_settings_manager
    from multi_device_settings import multi_device_settings_manager
    from database_manager import database_manager
    
    if request.method == 'GET':
        try:
            # 檢查是否指定了特定的 MAC ID
            mac_id = request.args.get('mac_id')
            
            if mac_id:
                # 獲取特定設備的設定
                settings = multi_device_settings_manager.load_device_settings(mac_id)
                return jsonify({'success': True, 'settings': settings, 'mac_id': mac_id})
            else:
                # 沒有指定 MAC ID，返回傳統的單一設備設定（向後相容）
                settings = device_settings_manager.load_settings()
                return jsonify({'success': True, 'settings': settings})
                
        except Exception as e:
            logging.error(f"獲取設備設定時發生錯誤: {e}")
            return jsonify({'success': False, 'message': f'獲取設定失敗: {str(e)}'})
    
    else:  # POST
        try:
            data = request.get_json()
            if not data:
                return jsonify({'success': False, 'message': '無效的請求資料'})
            
            # 驗證必要欄位
            if not data.get('device_name', '').strip():
                return jsonify({'success': False, 'message': '設備名稱不能為空'})
            
            # 檢查是否有 MAC ID (device_serial)
            mac_id = data.get('device_serial', '').strip()
            
            if mac_id:
                # 有 MAC ID，使用多設備管理器
                if multi_device_settings_manager.save_device_settings(mac_id, data):
                    # 同時將設備資訊保存到資料庫
                    try:
                        # 格式化設備型號
                        device_model = data.get('device_model', {})
                        if isinstance(device_model, dict):
                            # 將多頻道型號合併為字串
                            model_parts = []
                            for channel, model in device_model.items():
                                if model and model.strip():
                                    model_parts.append(f"Ch{channel}:{model}")
                            formatted_model = "; ".join(model_parts) if model_parts else "未設定"
                        else:
                            formatted_model = str(device_model) if device_model else "未設定"
                        
                        device_info = {
                            'mac_id': mac_id,
                            'device_name': data.get('device_name', ''),
                            'device_type': '感測器設備',
                            'device_model': formatted_model,
                            'factory_area': data.get('device_name', ''),  # 使用設備名稱作為廠區
                            'floor_level': '1F',  # 預設樓層，可以後續修改
                            'location_description': data.get('device_location', ''),
                            'installation_date': datetime.now().date().isoformat(),
                            'status': 'active'
                        }
                        database_manager.register_device(device_info)
                        logging.info(f"設備 {mac_id} 資訊已同步到資料庫")
                    except Exception as db_error:
                        logging.warning(f"設備資訊同步到資料庫失敗: {db_error}")
                    
                    response_data = {
                        'success': True, 
                        'message': f'設備 {mac_id} 的設定已成功儲存',
                        'mac_id': mac_id
                    }
                    
                    # 檢查是否需要重定向到 dashboard
                    redirect_to_dashboard = data.get('redirect_to_dashboard', False)
                    if redirect_to_dashboard:
                        response_data['redirect_url'] = url_for('integrated_dashboard.flask_dashboard')
                    
                    return jsonify(response_data)
                else:
                    return jsonify({'success': False, 'message': f'儲存設備 {mac_id} 設定時發生錯誤'})
            else:
                # 沒有 MAC ID，使用傳統的單一設備管理器（向後相容）
                if device_settings_manager.save_settings(data):
                    response_data = {
                        'success': True, 
                        'message': '設備設定已成功儲存'
                    }
                    
                    # 檢查是否需要重定向到 dashboard
                    redirect_to_dashboard = data.get('redirect_to_dashboard', False)
                    if redirect_to_dashboard:
                        response_data['redirect_url'] = url_for('integrated_dashboard.flask_dashboard')
                    
                    return jsonify(response_data)
                else:
                    return jsonify({'success': False, 'message': '儲存設定時發生錯誤'})
                
        except Exception as e:
            logging.error(f"儲存設備設定時發生錯誤: {e}")
            return jsonify({'success': False, 'message': f'處理請求時發生錯誤: {str(e)}'})


@integrated_device_bp.route('/api/multi-device-settings')
def api_multi_device_settings():
    """API: 獲取所有設備設定"""
    try:
        from multi_device_settings import multi_device_settings_manager
        settings = multi_device_settings_manager.get_all_device_settings()
        device_count = len(settings)
        
        return jsonify({
            'success': True,
            'devices': settings,
            'device_count': device_count
        })
    except Exception as e:
        logging.error(f"獲取多設備設定時發生錯誤: {e}")
        return jsonify({
            'success': False,
            'message': f'獲取設定失敗: {str(e)}'
        })