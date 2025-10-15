# controllers/integrated_uart_controller.py
from flask import Blueprint, request, jsonify
import logging

# 創建 Blueprint
integrated_uart_bp = Blueprint('integrated_uart', __name__)


@integrated_uart_bp.route('/api/uart/test', methods=['POST'])
def test_uart_connection():
    """API: 測試UART連接"""
    try:
        from uart_integrated import uart_reader
        success, message = uart_reader.test_uart_connection()
        return jsonify({'success': success, 'message': message})
    except Exception as e:
        return jsonify({'success': False, 'message': f'測試UART連接時發生錯誤: {str(e)}'})


@integrated_uart_bp.route('/api/uart/ports')
def list_uart_ports():
    """API: 列出可用的串口"""
    try:
        from uart_integrated import uart_reader
        ports = uart_reader.list_available_ports()
        return jsonify({'success': True, 'ports': ports})
    except Exception as e:
        return jsonify({'success': False, 'message': f'列出串口時發生錯誤: {str(e)}'})


@integrated_uart_bp.route('/api/uart/start', methods=['POST'])
def start_uart():
    """API: 開始UART讀取"""
    logging.info(f'API: 開始UART讀取, remote_addr={request.remote_addr}')
    
    try:
        from uart_integrated import uart_reader
        from config_manager import config_manager
        from network_utils import network_checker
        from models.dashboard_data_sender_model import DashboardDataSenderModel
        
        # 初始化相關管理器
        try:
            from multi_protocol_manager import offline_mode_manager
        except ImportError:
            offline_mode_manager = None
        
        dashboard_sender_model = DashboardDataSenderModel()
        dashboard_sender = dashboard_sender_model.get_sender()
        
        if uart_reader.is_running:
            return jsonify({'success': True, 'message': 'UART已在運行'})
        
        # 先測試UART連接
        test_success, test_message = uart_reader.test_uart_connection()
        if not test_success:
            # 列出可用串口
            available_ports = uart_reader.list_available_ports()
            port_info = ', '.join([f"{p['device']}({p['description']})" for p in available_ports]) if available_ports else "無可用串口"
            
            return jsonify({
                'success': False, 
                'message': f'UART連接測試失敗: {test_message}',
                'available_ports': available_ports,
                'suggestion': f'可用串口: {port_info}'
            })
        
        # 檢查網路狀態並自動設定離線模式
        try:
            network_status = network_checker.get_network_status()
            if not network_status['internet_available'] and offline_mode_manager:
                if not config_manager.get('offline_mode', False):
                    logging.info("偵測到無網路連接，自動啟用離線模式")
                    offline_mode_manager.enable_offline_mode()
        except Exception as network_error:
            logging.warning(f"網路檢查失敗，繼續以離線模式運行: {network_error}")
            if offline_mode_manager:
                offline_mode_manager.enable_offline_mode()
        
        # 檢查是否為離線模式
        offline_mode = config_manager.get('offline_mode', False)
        if offline_mode:
            logging.info("離線模式：UART讀取將在離線模式下啟動")
        
        if uart_reader.start_reading():
            message = 'UART讀取已開始'
            if offline_mode:
                message += '（離線模式）'
            else:
                # 在線模式下啟動資料發送到 Dashboard
                if dashboard_sender.enabled and not dashboard_sender.is_running:
                    if dashboard_sender.start(uart_reader):
                        message += '，資料發送服務已啟動'
                    else:
                        message += '，但資料發送服務啟動失敗'
            
            return jsonify({'success': True, 'message': message})
        else:
            # 提供更詳細的錯誤診斷
            available_ports = uart_reader.list_available_ports()
            com_port, _, _, _, _, _ = uart_reader.get_uart_config()
            
            error_details = {
                'success': False,
                'message': 'UART讀取啟動失敗',
                'details': {
                    'configured_port': com_port,
                    'available_ports': available_ports,
                    'suggestions': [
                        f'檢查設備是否連接: ls -la {com_port}',
                        '檢查用戶權限: sudo usermod -a -G dialout $USER',
                        '重新載入驅動: sudo modprobe ftdi_sio',
                        '檢查USB設備: lsusb',
                        '查看系統日誌: dmesg | tail'
                    ]
                }
            }
            
            return jsonify(error_details)
    except Exception as e:
        logging.exception(f'啟動UART時發生錯誤: {str(e)}')
        return jsonify({'success': False, 'message': f'啟動UART時發生錯誤: {str(e)}'})


@integrated_uart_bp.route('/api/uart/stop', methods=['POST'])
def stop_uart():
    """API: 停止UART讀取"""
    logging.info(f'API: 停止UART讀取, remote_addr={request.remote_addr}')
    
    try:
        from uart_integrated import uart_reader
        from models.dashboard_data_sender_model import DashboardDataSenderModel
        
        dashboard_sender_model = DashboardDataSenderModel()
        dashboard_sender = dashboard_sender_model.get_sender()
        
        uart_reader.stop_reading()
        
        # 同時停止資料發送服務
        message = 'UART讀取已停止'
        if dashboard_sender.is_running:
            if dashboard_sender.stop():
                message += '，資料發送服務已停止'
            else:
                message += '，但資料發送服務停止失敗'
        
        return jsonify({'success': True, 'message': message})
    except Exception as e:
        logging.exception(f'停止UART時發生錯誤: {str(e)}')
        return jsonify({'success': False, 'message': f'停止UART時發生錯誤: {str(e)}'})


@integrated_uart_bp.route('/api/uart/status')
def uart_status():
    """API: 獲取UART狀態"""
    try:
        from uart_integrated import uart_reader
        data = uart_reader.get_latest_data()
        return jsonify({
            'success': True,
            'is_running': uart_reader.is_running,
            'data_count': uart_reader.get_data_count(),
            'latest_data': data[-20:] if data else []  # 返回最新20筆資料
        })
    except Exception as e:
        return jsonify({'success': False, 'message': f'獲取UART狀態時發生錯誤: {str(e)}'})


@integrated_uart_bp.route('/api/uart/clear', methods=['POST'])
def clear_uart_data():
    """API: 清除UART資料"""
    try:
        from uart_integrated import uart_reader
        uart_reader.clear_data()
        return jsonify({'success': True, 'message': 'UART資料已清除'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'清除UART資料時發生錯誤: {str(e)}'})


@integrated_uart_bp.route('/api/uart/mac-ids', methods=['GET'])
def get_uart_mac_ids():
    """API: 獲取UART接收到的MAC ID列表"""
    try:
        logging.info(f'API請求: /api/uart/mac-ids from {request.remote_addr}')
        
        from uart_integrated import uart_reader
        
        data = uart_reader.get_latest_data()
        logging.info(f'UART數據總數: {len(data) if data else 0}')
        data_source = 'UART即時數據'
        
        # 修正：如果即時數據為空或MAC ID數量少於預期，強制載入歷史數據
        if not data or len(set(entry.get('mac_id') for entry in data if entry.get('mac_id') and entry.get('mac_id') not in ['N/A', '', None])) < 1:
            logging.info('即時數據不足，嘗試從歷史文件載入MAC ID')
            uart_reader.load_historical_data(days_back=90)  # 載入最近90天的數據
            data = uart_reader.get_latest_data()
            data_source = '歷史文件增強載入'
            logging.info(f'從歷史文件增強載入數據: {len(data) if data else 0} 筆')
            
        if not data:
            logging.warning('沒有可用的UART數據')
            return jsonify({
                'success': True, 
                'mac_ids': [], 
                'data_source': data_source,
                'message': '暫無UART數據，請先啟動UART讀取或檢查歷史數據'
            })
        
        # 從UART數據中提取所有的MAC ID
        mac_ids = []
        valid_mac_count = 0
        
        for entry in data:
            mac_id = entry.get('mac_id')
            if mac_id and mac_id not in ['N/A', '', None]:
                valid_mac_count += 1
                mac_ids.append(mac_id)
        
        # 去重複並排序
        unique_mac_ids = sorted(list(set(mac_ids)))
        
        logging.info(f'MAC ID 處理結果: 總數據{len(data)}, 有效MAC數據{valid_mac_count}, 唯一MAC ID數{len(unique_mac_ids)}')
        if unique_mac_ids:
            logging.info(f'找到的 MAC IDs: {unique_mac_ids}')

        return jsonify({
            'success': True,
            'mac_ids': unique_mac_ids,
            'data_source': data_source,
            'total_entries': len(data),
            'valid_mac_entries': valid_mac_count,
            'unique_mac_count': len(unique_mac_ids)
        })
        
    except Exception as e:
        logging.exception(f'獲取MAC ID列表時發生錯誤: {str(e)}')
        return jsonify({
            'success': False,
            'message': f'獲取MAC ID列表時發生錯誤: {str(e)}'
        }), 500


@integrated_uart_bp.route('/api/uart/mac-channels/', methods=['GET'])
@integrated_uart_bp.route('/api/uart/mac-channels/<mac_id>', methods=['GET'])
def get_uart_mac_channels(mac_id=None):
    """API: 獲取指定 MAC ID 的通道資訊"""
    try:
        logging.info(f'API請求: /api/uart/mac-channels/{mac_id or "all"} from {request.remote_addr}')
        
        from uart_integrated import uart_reader
        
        # 獲取最新數據
        data = uart_reader.get_latest_data()
        
        if not data:
            logging.warning('沒有可用的UART數據')
            return jsonify({
                'success': True,
                'channels': [],
                'message': '暫無UART數據，請先啟動UART讀取'
            })
        
        if mac_id:
            # 獲取指定 MAC ID 的通道資訊
            mac_channels = []
            valid_channels = set()  # 用於收集有效頻道（0-6）
            
            for entry in data:
                if entry.get('mac_id') == mac_id:
                    channel = entry.get('channel', 'N/A')
                    
                    # 檢查頻道是否在有效範圍內（0-6）
                    try:
                        channel_num = int(channel)
                        if 0 <= channel_num <= 6:
                            valid_channels.add(channel_num)
                            
                            channel_info = {
                                'timestamp': entry.get('timestamp', ''),
                                'channel': channel_num,
                                'current': entry.get('current', 0),
                                'temperature': entry.get('temperature', 0),
                                'power': entry.get('power', 0),
                                'voltage': entry.get('voltage', 0),
                                'frequency': entry.get('frequency', 0),
                                'power_factor': entry.get('power_factor', 0)
                            }
                            mac_channels.append(channel_info)
                    except (ValueError, TypeError):
                        # 忽略無效的頻道值
                        continue
            
            # 按時間戳排序（最新的在前）
            mac_channels.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
            
            # 轉換有效頻道為排序列表
            valid_channels_list = sorted(list(valid_channels))
            
            return jsonify({
                'success': True,
                'mac_id': mac_id,
                'channels': valid_channels_list,  # 只返回有效頻道號列表
                'channel_data': mac_channels,     # 詳細資料
                'total_records': len(mac_channels),
                'data_source': 'UART實時數據' if mac_channels else '無有效數據'
            })
        else:
            # 獲取所有 MAC ID 的通道摘要
            mac_summary = {}
            for entry in data:
                mac = entry.get('mac_id')
                if mac and mac not in ['N/A', '', None]:
                    if mac not in mac_summary:
                        mac_summary[mac] = {
                            'mac_id': mac,
                            'channels': set(),
                            'latest_timestamp': '',
                            'total_records': 0
                        }
                    
                    # 檢查頻道是否在有效範圍內（0-6）
                    channel = entry.get('channel', 'N/A')
                    try:
                        channel_num = int(channel)
                        if 0 <= channel_num <= 6:
                            mac_summary[mac]['channels'].add(channel_num)
                            mac_summary[mac]['total_records'] += 1
                            
                            # 更新最新時間戳
                            timestamp = entry.get('timestamp', '')
                            if timestamp > mac_summary[mac]['latest_timestamp']:
                                mac_summary[mac]['latest_timestamp'] = timestamp
                    except (ValueError, TypeError):
                        # 忽略無效的頻道值
                        continue
            
            # 轉換為列表格式
            result = []
            for mac, info in mac_summary.items():
                result.append({
                    'mac_id': mac,
                    'channels': sorted(list(info['channels'])),
                    'channel_count': len(info['channels']),
                    'latest_timestamp': info['latest_timestamp'],
                    'total_records': info['total_records']
                })
            
            # 按 MAC ID 排序
            result.sort(key=lambda x: x['mac_id'])
            
            return jsonify({
                'success': True,
                'mac_channels': result,
                'total_mac_ids': len(result)
            })
        
    except Exception as e:
        logging.exception(f'獲取MAC通道資訊時發生錯誤: {str(e)}')
        return jsonify({
            'success': False,
            'message': f'獲取MAC通道資訊時發生錯誤: {str(e)}'
        }), 500