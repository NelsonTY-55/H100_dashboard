"""
設備控制器 - MVC 架構
處理設備設定和管理相關的路由
"""

from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
import logging
from datetime import datetime

# 創建 Blueprint
device_bp = Blueprint('device', __name__)

# 全域變數，將在初始化時設置
device_settings_manager = None
multi_device_settings_manager = None

def init_controller(device_settings_mgr, multi_device_settings_mgr):
    """初始化控制器"""
    global device_settings_manager, multi_device_settings_manager
    device_settings_manager = device_settings_mgr
    multi_device_settings_manager = multi_device_settings_mgr

@device_bp.route('/db-setting')
def db_setting():
    """設備設定頁面"""
    logging.info(f'訪問設備設定頁面, remote_addr={request.remote_addr}')
    
    # 檢查是否從 dashboard 重定向過來
    redirect_to_dashboard = request.args.get('redirect', 'false').lower() == 'true'
    
    # 載入當前設備設定
    try:
        current_settings = device_settings_manager.load_settings() if device_settings_manager else {}
    except Exception as e:
        logging.error(f"載入設備設定時發生錯誤: {e}")
        current_settings = {}
    
    return render_template('db_setting.html', 
                         current_settings=current_settings,
                         redirect_to_dashboard=redirect_to_dashboard)

@device_bp.route('/api/device-settings', methods=['GET', 'POST'])
def api_device_settings():
    """API: 獲取或儲存設備設定，支援多設備"""
    if request.method == 'GET':
        try:
            # 檢查是否指定了特定的 MAC ID
            mac_id = request.args.get('mac_id')
            
            if mac_id and multi_device_settings_manager:
                # 獲取特定設備的設定
                settings = multi_device_settings_manager.load_device_settings(mac_id)
                return jsonify({'success': True, 'settings': settings, 'mac_id': mac_id})
            else:
                # 沒有指定 MAC ID，返回傳統的單一設備設定（向後相容）
                settings = device_settings_manager.load_settings() if device_settings_manager else {}
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
            
            if mac_id and multi_device_settings_manager:
                # 有 MAC ID，使用多設備管理器
                if multi_device_settings_manager.save_device_settings(mac_id, data):
                    response_data = {
                        'success': True, 
                        'message': f'設備 {mac_id} 的設定已成功儲存',
                        'mac_id': mac_id
                    }
                    logging.info(f"設備 {mac_id} 設定已更新: {data.get('device_name')}")
                    return jsonify(response_data)
                else:
                    return jsonify({'success': False, 'message': f'儲存設備 {mac_id} 設定失敗'})
            else:
                # 沒有 MAC ID，使用傳統的單一設備管理器（向後相容）
                if device_settings_manager and device_settings_manager.save_settings(data):
                    response_data = {
                        'success': True, 
                        'message': '設備設定已成功儲存'
                    }
                    logging.info(f"設備設定已更新: {data.get('device_name')}")
                    return jsonify(response_data)
                else:
                    return jsonify({'success': False, 'message': '儲存設定失敗'})
                
        except Exception as e:
            logging.error(f"儲存設備設定時發生錯誤: {e}")
            return jsonify({'success': False, 'message': f'處理請求時發生錯誤: {str(e)}'})

@device_bp.route('/api/multi-device-settings')
def api_multi_device_settings():
    """API: 獲取所有設備設定"""
    try:
        if not multi_device_settings_manager:
            return jsonify({
                'success': False,
                'message': '多設備管理器未初始化',
                'devices': {}
            })
            
        all_devices = multi_device_settings_manager.load_all_devices()
        return jsonify({
            'success': True,
            'devices': all_devices,
            'device_count': len(all_devices),
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        logging.error(f"獲取多設備設定時發生錯誤: {e}")
        return jsonify({
            'success': False,
            'message': f'獲取多設備設定失敗: {str(e)}',
            'devices': {}
        })

@device_bp.route('/api/dashboard/areas')
def api_dashboard_areas():
    """API: 獲取所有廠區、位置、設備型號統計資料"""
    try:
        if not multi_device_settings_manager:
            return jsonify({
                'success': False,
                'message': '多設備管理器未初始化',
                'areas': [],
                'locations': [],
                'models': []
            })
            
        all_devices = multi_device_settings_manager.load_all_devices()
        
        # 統計廠區 (device_name)
        areas = set()
        locations = set()
        models = set()
        
        for mac_id, device_setting in all_devices.items():
            # 廠區對應 device_name
            if device_setting.get('device_name'):
                areas.add(device_setting['device_name'])
            
            # 設備位置對應 device_location    
            if device_setting.get('device_location'):
                locations.add(device_setting['device_location'])
            
            # 設備型號處理
            device_model = device_setting.get('device_model', '')
            if isinstance(device_model, dict):
                # 如果是字典格式（多頻道型號）
                for channel, model in device_model.items():
                    if model and model.strip():
                        models.add(model.strip())
            elif isinstance(device_model, str) and device_model.strip():
                models.add(device_model.strip())
        
        return jsonify({
            'success': True,
            'areas': sorted(list(areas)),
            'locations': sorted(list(locations)),
            'models': sorted(list(models)),
            'device_count': len(all_devices),
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logging.error(f"獲取廠區統計資料時發生錯誤: {e}")
        return jsonify({
            'success': False,
            'message': f'獲取廠區統計資料失敗: {str(e)}',
            'areas': [],
            'locations': [],
            'models': []
        })