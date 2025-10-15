"""
即時監控 API 控制器
提供 RAS_pi 連接狀態、即時資料監控和智能觸發管理的 API 端點
"""

from flask import Blueprint, jsonify, request
import logging
from datetime import datetime
from typing import Dict, Any

from services.raspi_api_client import get_raspi_client, get_raspi_aggregator, RaspberryPiConfig
from services.real_time_data_service import get_real_time_service
from services.smart_uart_trigger import get_trigger_manager, UARTScanConfig


# 創建 Blueprint
realtime_api_bp = Blueprint('realtime_api', __name__, url_prefix='/api/realtime')

logger = logging.getLogger(__name__)


@realtime_api_bp.route('/status')
def get_realtime_status():
    """獲取即時監控系統整體狀態"""
    try:
        # 獲取各個服務的狀態
        raspi_client = get_raspi_client()
        real_time_service = get_real_time_service()
        trigger_manager = get_trigger_manager()
        
        # RAS_pi 連接狀態
        raspi_connection = raspi_client.get_connection_status()
        
        # 即時資料服務狀態
        realtime_service_status = real_time_service.get_service_status()
        
        # 觸發管理器狀態
        trigger_status = trigger_manager.get_status()
        
        # 系統整體狀態評估
        overall_health = _assess_system_health(
            raspi_connection, 
            realtime_service_status, 
            trigger_status
        )
        
        return jsonify({
            'success': True,
            'timestamp': datetime.now().isoformat(),
            'overall_health': overall_health,
            'components': {
                'raspi_connection': raspi_connection,
                'realtime_service': realtime_service_status,
                'trigger_manager': trigger_status
            }
        })
        
    except Exception as e:
        logger.error(f"獲取即時狀態失敗: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500


@realtime_api_bp.route('/raspi/status')
def get_raspi_status():
    """獲取 RAS_pi 詳細狀態"""
    try:
        aggregator = get_raspi_aggregator()
        complete_status = aggregator.get_complete_status()
        
        return jsonify({
            'success': True,
            'data': complete_status,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"獲取 RAS_pi 狀態失敗: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500


@realtime_api_bp.route('/raspi/uart/summary')
def get_raspi_uart_summary():
    """獲取 RAS_pi UART 即時摘要"""
    try:
        aggregator = get_raspi_aggregator()
        uart_summary = aggregator.get_real_time_uart_summary()
        
        return jsonify({
            'success': True,
            'data': uart_summary,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"獲取 UART 摘要失敗: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500


@realtime_api_bp.route('/raspi/uart/mac-data/<mac_id>')
def get_raspi_mac_data(mac_id):
    """獲取 RAS_pi 特定 MAC ID 的即時資料"""
    try:
        minutes = request.args.get('minutes', 10, type=int)
        
        raspi_client = get_raspi_client()
        success, data = raspi_client.get_uart_mac_data(mac_id, minutes)
        
        if success:
            return jsonify({
                'success': True,
                'mac_id': mac_id,
                'minutes': minutes,
                'data': data,
                'timestamp': datetime.now().isoformat()
            })
        else:
            return jsonify({
                'success': False,
                'mac_id': mac_id,
                'error': 'Failed to fetch data from RAS_pi',
                'timestamp': datetime.now().isoformat()
            }), 500
            
    except Exception as e:
        logger.error(f"獲取 MAC 資料失敗: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500


@realtime_api_bp.route('/service/start', methods=['POST'])
def start_realtime_service():
    """啟動即時監控服務"""
    try:
        real_time_service = get_real_time_service()
        
        if real_time_service.is_running:
            return jsonify({
                'success': True,
                'message': '即時監控服務已在運行',
                'timestamp': datetime.now().isoformat()
            })
        
        success = real_time_service.start()
        
        if success:
            return jsonify({
                'success': True,
                'message': '即時監控服務已啟動',
                'timestamp': datetime.now().isoformat()
            })
        else:
            return jsonify({
                'success': False,
                'message': '即時監控服務啟動失敗',
                'timestamp': datetime.now().isoformat()
            }), 500
            
    except Exception as e:
        logger.error(f"啟動即時監控服務失敗: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500


@realtime_api_bp.route('/service/stop', methods=['POST'])
def stop_realtime_service():
    """停止即時監控服務"""
    try:
        real_time_service = get_real_time_service()
        
        if not real_time_service.is_running:
            return jsonify({
                'success': True,
                'message': '即時監控服務未在運行',
                'timestamp': datetime.now().isoformat()
            })
        
        success = real_time_service.stop()
        
        if success:
            return jsonify({
                'success': True,
                'message': '即時監控服務已停止',
                'timestamp': datetime.now().isoformat()
            })
        else:
            return jsonify({
                'success': False,
                'message': '即時監控服務停止失敗',
                'timestamp': datetime.now().isoformat()
            }), 500
            
    except Exception as e:
        logger.error(f"停止即時監控服務失敗: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500


@realtime_api_bp.route('/trigger/start', methods=['POST'])
def start_trigger_manager():
    """啟動智能觸發管理器"""
    try:
        trigger_manager = get_trigger_manager()
        
        if trigger_manager.is_active:
            return jsonify({
                'success': True,
                'message': '智能觸發管理器已在運行',
                'timestamp': datetime.now().isoformat()
            })
        
        success = trigger_manager.start()
        
        if success:
            return jsonify({
                'success': True,
                'message': '智能觸發管理器已啟動',
                'timestamp': datetime.now().isoformat()
            })
        else:
            return jsonify({
                'success': False,
                'message': '智能觸發管理器啟動失敗',
                'timestamp': datetime.now().isoformat()
            }), 500
            
    except Exception as e:
        logger.error(f"啟動智能觸發管理器失敗: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500


@realtime_api_bp.route('/trigger/stop', methods=['POST'])
def stop_trigger_manager():
    """停止智能觸發管理器"""
    try:
        trigger_manager = get_trigger_manager()
        
        if not trigger_manager.is_active:
            return jsonify({
                'success': True,
                'message': '智能觸發管理器未在運行',
                'timestamp': datetime.now().isoformat()
            })
        
        success = trigger_manager.stop()
        
        if success:
            return jsonify({
                'success': True,
                'message': '智能觸發管理器已停止',
                'timestamp': datetime.now().isoformat()
            })
        else:
            return jsonify({
                'success': False,
                'message': '智能觸發管理器停止失敗',
                'timestamp': datetime.now().isoformat()
            }), 500
            
    except Exception as e:
        logger.error(f"停止智能觸發管理器失敗: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500


@realtime_api_bp.route('/trigger/manual', methods=['POST'])
def manual_trigger_scan():
    """手動觸發掃描"""
    try:
        data = request.get_json() or {}
        message = data.get('message', '手動觸發掃描')
        
        trigger_manager = get_trigger_manager()
        
        if not trigger_manager.is_active:
            return jsonify({
                'success': False,
                'message': '智能觸發管理器未啟動',
                'timestamp': datetime.now().isoformat()
            }), 400
        
        success = trigger_manager.manual_scan(message)
        
        if success:
            return jsonify({
                'success': True,
                'message': f'手動掃描已觸發: {message}',
                'timestamp': datetime.now().isoformat()
            })
        else:
            return jsonify({
                'success': False,
                'message': '手動觸發失敗',
                'timestamp': datetime.now().isoformat()
            }), 500
            
    except Exception as e:
        logger.error(f"手動觸發掃描失敗: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500


@realtime_api_bp.route('/config', methods=['GET', 'POST'])
def manage_realtime_config():
    """管理即時監控配置"""
    if request.method == 'GET':
        try:
            # 獲取當前配置
            real_time_service = get_real_time_service()
            trigger_manager = get_trigger_manager()
            
            current_config = {
                'raspi_config': {
                    'host': real_time_service.raspi_config.host,
                    'port': real_time_service.raspi_config.port,
                    'timeout': real_time_service.raspi_config.timeout,
                    'retry_count': real_time_service.raspi_config.retry_count,
                    'poll_interval': real_time_service.raspi_config.poll_interval
                },
                'trigger_config': {
                    'min_scan_interval': trigger_manager.scan_config.min_scan_interval,
                    'max_scan_interval': trigger_manager.scan_config.max_scan_interval,
                    'adaptive_scanning': trigger_manager.scan_config.adaptive_scanning,
                    'priority_mac_ids': trigger_manager.scan_config.priority_mac_ids,
                    'scan_timeout': trigger_manager.scan_config.scan_timeout
                }
            }
            
            return jsonify({
                'success': True,
                'config': current_config,
                'timestamp': datetime.now().isoformat()
            })
            
        except Exception as e:
            logger.error(f"獲取配置失敗: {e}")
            return jsonify({
                'success': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }), 500
    
    else:  # POST
        try:
            data = request.get_json()
            if not data:
                return jsonify({
                    'success': False,
                    'message': '無效的請求資料',
                    'timestamp': datetime.now().isoformat()
                }), 400
            
            updated_fields = []
            
            # 更新即時服務配置
            service_updates = {}
            raspi_config = data.get('raspi_config', {})
            for key in ['poll_interval']:
                if key in raspi_config:
                    service_updates[key] = raspi_config[key]
                    updated_fields.append(f"raspi_{key}")
            
            if service_updates:
                real_time_service = get_real_time_service()
                real_time_service.update_config(**service_updates)
            
            # 更新觸發管理器配置
            trigger_updates = {}
            trigger_config = data.get('trigger_config', {})
            for key in ['min_scan_interval', 'max_scan_interval', 'adaptive_scanning', 
                       'priority_mac_ids', 'scan_timeout']:
                if key in trigger_config:
                    trigger_updates[key] = trigger_config[key]
                    updated_fields.append(f"trigger_{key}")
            
            if trigger_updates:
                trigger_manager = get_trigger_manager()
                trigger_manager.update_scan_config(**trigger_updates)
            
            return jsonify({
                'success': True,
                'message': f'配置已更新: {", ".join(updated_fields)}' if updated_fields else '無配置更新',
                'updated_fields': updated_fields,
                'timestamp': datetime.now().isoformat()
            })
            
        except Exception as e:
            logger.error(f"更新配置失敗: {e}")
            return jsonify({
                'success': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }), 500


@realtime_api_bp.route('/statistics')
def get_realtime_statistics():
    """獲取即時監控系統統計資料"""
    try:
        real_time_service = get_real_time_service()
        trigger_manager = get_trigger_manager()
        
        service_status = real_time_service.get_service_status()
        trigger_status = trigger_manager.get_status()
        
        # 綜合統計
        combined_stats = {
            'system_uptime': service_status.get('uptime_seconds'),
            'total_raspi_checks': service_status.get('stats', {}).get('total_checks', 0),
            'successful_raspi_checks': service_status.get('stats', {}).get('successful_checks', 0),
            'total_scans_triggered': trigger_status.get('statistics', {}).get('total_scans', 0),
            'successful_scans': trigger_status.get('statistics', {}).get('successful_scans', 0),
            'mac_ids_discovered': len(service_status.get('stats', {}).get('mac_ids_discovered', [])),
            'current_activity_level': trigger_status.get('adaptive_state', {}).get('activity_level', 'unknown'),
            'last_successful_check': service_status.get('last_successful_check'),
            'last_scan_time': trigger_status.get('last_scan_time')
        }
        
        return jsonify({
            'success': True,
            'statistics': combined_stats,
            'detailed_stats': {
                'realtime_service': service_status.get('stats', {}),
                'trigger_manager': trigger_status.get('statistics', {}),
                'adaptive_state': trigger_status.get('adaptive_state', {})
            },
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"獲取統計資料失敗: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500


@realtime_api_bp.route('/health')
def health_check():
    """即時監控系統健康檢查"""
    try:
        # 快速健康檢查
        raspi_client = get_raspi_client()
        real_time_service = get_real_time_service()
        trigger_manager = get_trigger_manager()
        
        health_status = {
            'raspi_connected': raspi_client.is_connected,
            'realtime_service_running': real_time_service.is_running,
            'trigger_manager_active': trigger_manager.is_active,
            'overall_healthy': False
        }
        
        # 綜合健康評估
        health_status['overall_healthy'] = (
            health_status['raspi_connected'] and 
            health_status['realtime_service_running'] and 
            health_status['trigger_manager_active']
        )
        
        status_code = 200 if health_status['overall_healthy'] else 503
        
        return jsonify({
            'success': True,
            'health': health_status,
            'timestamp': datetime.now().isoformat()
        }), status_code
        
    except Exception as e:
        logger.error(f"健康檢查失敗: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500


def _assess_system_health(raspi_connection: Dict, realtime_status: Dict, trigger_status: Dict) -> Dict:
    """評估系統整體健康狀態"""
    health = {
        'status': 'unknown',
        'score': 0,
        'issues': [],
        'recommendations': []
    }
    
    # RAS_pi 連接評估
    if not raspi_connection.get('connected', False):
        health['issues'].append('RAS_pi 連接中斷')
        health['recommendations'].append('檢查網路連接和 RAS_pi 服務狀態')
    else:
        health['score'] += 30
    
    # 即時服務評估
    if not realtime_status.get('running', False):
        health['issues'].append('即時資料服務未運行')
        health['recommendations'].append('啟動即時資料監控服務')
    else:
        health['score'] += 35
        
        # 檢查服務品質
        stats = realtime_status.get('stats', {})
        total_checks = stats.get('total_checks', 0)
        successful_checks = stats.get('successful_checks', 0)
        
        if total_checks > 0:
            success_rate = successful_checks / total_checks
            if success_rate < 0.8:
                health['issues'].append(f'即時服務成功率偏低 ({success_rate:.1%})')
                health['recommendations'].append('檢查網路穩定性和 RAS_pi 服務狀態')
    
    # 觸發管理器評估
    if not trigger_status.get('active', False):
        health['issues'].append('智能觸發管理器未啟動')
        health['recommendations'].append('啟動智能 UART 觸發管理器')
    else:
        health['score'] += 35
    
    # 綜合評分
    if health['score'] >= 90:
        health['status'] = 'excellent'
    elif health['score'] >= 70:
        health['status'] = 'good'
    elif health['score'] >= 50:
        health['status'] = 'fair'
    elif health['score'] >= 30:
        health['status'] = 'poor'
    else:
        health['status'] = 'critical'
    
    return health


# 控制器初始化函數
def init_realtime_api_controller():
    """初始化即時監控 API 控制器"""
    logger.info("即時監控 API 控制器已初始化")
    
    # 這裡可以進行一些初始化設定
    # 例如：設置默認配置、檢查依賴等
    
    try:
        # 嘗試初始化各個服務（但不自動啟動）
        get_raspi_client()
        get_real_time_service()
        get_trigger_manager()
        
        logger.info("即時監控服務組件初始化完成")
        return True
        
    except Exception as e:
        logger.error(f"即時監控 API 控制器初始化失敗: {e}")
        return False