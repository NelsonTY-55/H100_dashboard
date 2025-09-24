"""
系統模式控制器
處理系統模式切換相關的路由
"""

from flask import Blueprint, request, jsonify
import logging
from datetime import datetime

# 創建 Blueprint
mode_bp = Blueprint('mode', __name__)

# 系統模式狀態
current_mode = {'mode': 'idle', 'last_change': datetime.now().isoformat()}


@mode_bp.route('/get-mode', methods=['GET'])
def get_mode():
    """獲取當前系統模式"""
    try:
        mode_info = {
            'current_mode': current_mode['mode'],
            'last_change': current_mode['last_change'],
            'available_modes': [
                {
                    'name': 'idle',
                    'description': '待機模式',
                    'power_consumption': 'low'
                },
                {
                    'name': 'monitor',
                    'description': '監控模式',
                    'power_consumption': 'medium'
                },
                {
                    'name': 'active',
                    'description': '活動模式',
                    'power_consumption': 'high'
                },
                {
                    'name': 'maintenance',
                    'description': '維護模式',
                    'power_consumption': 'low'
                }
            ],
            'mode_history': [
                {
                    'mode': 'active',
                    'start_time': '2025-09-23T08:00:00',
                    'end_time': '2025-09-23T12:00:00',
                    'duration': '4 hours'
                },
                {
                    'mode': 'monitor',
                    'start_time': '2025-09-23T12:00:00',
                    'end_time': '2025-09-23T18:00:00',
                    'duration': '6 hours'
                }
            ]
        }
        
        return jsonify({
            'success': True,
            'data': mode_info
        })
        
    except Exception as e:
        logging.error(f"獲取系統模式時發生錯誤: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@mode_bp.route('/set-mode', methods=['POST'])
def set_mode():
    """設定系統模式"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': '沒有接收到模式數據'
            }), 400
        
        new_mode = data.get('mode')
        if not new_mode:
            return jsonify({
                'success': False,
                'error': '缺少模式參數'
            }), 400
        
        # 驗證模式是否有效
        valid_modes = ['idle', 'monitor', 'active', 'maintenance']
        if new_mode not in valid_modes:
            return jsonify({
                'success': False,
                'error': f'無效的模式: {new_mode}，有效模式: {valid_modes}'
            }), 400
        
        # 記錄模式切換
        old_mode = current_mode['mode']
        current_mode['mode'] = new_mode
        current_mode['last_change'] = datetime.now().isoformat()
        
        # 模式切換邏輯
        mode_actions = {
            'idle': {
                'description': '系統進入待機狀態',
                'actions': ['停止數據收集', '降低系統功耗', '保持基本監控']
            },
            'monitor': {
                'description': '系統進入監控狀態',
                'actions': ['開始數據收集', '啟用即時監控', '設定警報閾值']
            },
            'active': {
                'description': '系統進入活動狀態',
                'actions': ['全功能運作', '高頻數據收集', '即時分析處理']
            },
            'maintenance': {
                'description': '系統進入維護狀態',
                'actions': ['暫停正常操作', '啟用診斷模式', '準備維護工具']
            }
        }
        
        mode_info = mode_actions.get(new_mode, {})
        
        # 這裡可以添加實際的模式切換邏輯
        # 例如啟動/停止特定服務、調整監控頻率等
        
        result = {
            'previous_mode': old_mode,
            'current_mode': new_mode,
            'change_time': current_mode['last_change'],
            'description': mode_info.get('description', ''),
            'actions_taken': mode_info.get('actions', []),
            'parameters': data.get('parameters', {}),
            'estimated_power_consumption': {
                'idle': '低',
                'monitor': '中等',
                'active': '高',
                'maintenance': '低'
            }.get(new_mode, '未知')
        }
        
        logging.info(f"系統模式已從 {old_mode} 切換到 {new_mode}")
        
        return jsonify({
            'success': True,
            'message': f'系統模式已切換到 {new_mode}',
            'data': result
        })
        
    except Exception as e:
        logging.error(f"設定系統模式時發生錯誤: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@mode_bp.route('/mode-status', methods=['GET'])
def mode_status():
    """獲取模式狀態詳情"""
    try:
        mode = current_mode['mode']
        
        # 根據模式返回狀態資訊
        status_details = {
            'idle': {
                'services_active': ['基本監控', '網路連接'],
                'services_inactive': ['數據收集', '即時分析', 'UART讀取'],
                'power_level': 20,
                'expected_actions': ['等待指令', '保持連接']
            },
            'monitor': {
                'services_active': ['基本監控', '網路連接', '數據收集', 'UART讀取'],
                'services_inactive': ['高頻分析', '預測分析'],
                'power_level': 60,
                'expected_actions': ['收集數據', '監控設備狀態', '記錄日誌']
            },
            'active': {
                'services_active': ['所有服務'],
                'services_inactive': [],
                'power_level': 95,
                'expected_actions': ['全功能運作', '即時分析', '自動決策']
            },
            'maintenance': {
                'services_active': ['基本監控', '診斷工具'],
                'services_inactive': ['正常數據處理', '自動化操作'],
                'power_level': 30,
                'expected_actions': ['系統診斷', '維護檢查', '故障排除']
            }
        }
        
        current_status = status_details.get(mode, {
            'services_active': [],
            'services_inactive': [],
            'power_level': 0,
            'expected_actions': []
        })
        
        result = {
            'current_mode': mode,
            'mode_start_time': current_mode['last_change'],
            'runtime': '計算運行時間',  # 這裡應該計算實際運行時間
            'status': current_status,
            'system_health': {
                'cpu_usage': 25,  # 應該從實際系統獲取
                'memory_usage': 45,
                'disk_usage': 60,
                'network_status': 'connected'
            },
            'next_scheduled_action': {
                'action': '例行檢查',
                'scheduled_time': '2025-09-24T02:00:00'
            }
        }
        
        return jsonify({
            'success': True,
            'data': result
        })
        
    except Exception as e:
        logging.error(f"獲取模式狀態時發生錯誤: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500