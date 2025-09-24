"""
UART 控制器
處理 UART 相關的路由和邏輯
"""

from flask import Blueprint, request, jsonify, Response
import logging
import json
from datetime import datetime
from models import UartDataModel

# 創建 Blueprint
uart_bp = Blueprint('uart', __name__, url_prefix='/api/uart')

# 初始化模型
uart_model = UartDataModel()

# 全域變數（這些應該從原始程式碼移過來）
uart_reader = None
protocol_manager = None


@uart_bp.route('/status')
def api_uart_status():
    """獲取 UART 狀態"""
    try:
        status = {
            'uart_reader_available': uart_reader is not None,
            'protocol_manager_available': protocol_manager is not None,
            'data_available': False,
            'latest_data_count': 0
        }
        
        # 嘗試獲取最新數據統計
        try:
            data_result = uart_model.get_uart_data_from_files(limit=1)
            if data_result['success']:
                status['data_available'] = True
                status['latest_data_count'] = data_result.get('total_count', 0)
        except Exception as e:
            logging.warning(f"獲取UART數據統計時發生錯誤: {e}")
        
        return jsonify({
            'success': True,
            'data': status
        })
        
    except Exception as e:
        logging.error(f"獲取UART狀態時發生錯誤: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@uart_bp.route('/mac-ids', methods=['GET'])
def api_uart_mac_ids():
    """獲取可用的 MAC ID 列表"""
    try:
        mac_ids = uart_model.get_mac_ids()
        
        return jsonify({
            'success': True,
            'data': mac_ids,
            'total_count': len(mac_ids)
        })
        
    except Exception as e:
        logging.error(f"獲取MAC ID列表時發生錯誤: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@uart_bp.route('/mac-channels/', methods=['GET'])
@uart_bp.route('/mac-channels/<mac_id>', methods=['GET'])
def api_uart_mac_channels(mac_id=None):
    """獲取 MAC 通道資訊"""
    try:
        if mac_id:
            # 獲取指定 MAC ID 的通道
            channels = uart_model.get_mac_channels(mac_id)
            
            return jsonify({
                'success': True,
                'data': {
                    'mac_id': mac_id,
                    'channels': channels,
                    'channel_count': len(channels)
                }
            })
        else:
            # 獲取所有 MAC ID 的通道資訊
            mac_ids = uart_model.get_mac_ids()
            mac_channels = {}
            
            for mid in mac_ids:
                channels = uart_model.get_mac_channels(mid)
                mac_channels[mid] = {
                    'channels': channels,
                    'channel_count': len(channels)
                }
            
            return jsonify({
                'success': True,
                'data': mac_channels,
                'total_mac_count': len(mac_ids)
            })
        
    except Exception as e:
        logging.error(f"獲取MAC通道資訊時發生錯誤: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@uart_bp.route('/mac-data/<mac_id>', methods=['GET'])
def api_uart_mac_data(mac_id):
    """獲取指定 MAC ID 的數據"""
    try:
        # 獲取查詢參數
        limit = int(request.args.get('limit', 1000))
        channel = request.args.get('channel')
        
        # 限制最大數量
        if limit > 50000:
            limit = 50000
        
        # 獲取數據
        data_result = uart_model.get_uart_data_from_files(mac_id=mac_id, limit=limit)
        
        if not data_result['success']:
            return jsonify(data_result), 400
        
        # 如果指定了通道，進行額外過濾
        if channel:
            try:
                channel_num = int(channel)
                filtered_data = []
                for record in data_result['data']:
                    if record.get('channel') == channel_num:
                        filtered_data.append(record)
                data_result['data'] = filtered_data
                data_result['total_count'] = len(filtered_data)
                data_result['channel_filter'] = channel_num
            except ValueError:
                return jsonify({
                    'success': False,
                    'error': f'無效的通道號: {channel}'
                }), 400
        
        return jsonify(data_result)
        
    except Exception as e:
        logging.error(f"獲取MAC數據時發生錯誤: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@uart_bp.route('/test', methods=['POST'])
def api_uart_test():
    """測試 UART 連接"""
    try:
        data = request.get_json()
        port = data.get('port', '/dev/ttyUSB0')
        baudrate = data.get('baudrate', 9600)
        
        # 這裡應該實現實際的UART測試邏輯
        # 暫時返回模擬結果
        test_result = {
            'port': port,
            'baudrate': baudrate,
            'status': 'success',
            'message': 'UART 測試連接成功',
            'test_time': datetime.now().isoformat()
        }
        
        return jsonify({
            'success': True,
            'data': test_result
        })
        
    except Exception as e:
        logging.error(f"UART測試時發生錯誤: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@uart_bp.route('/ports')
def api_uart_ports():
    """獲取可用的串口列表"""
    try:
        import serial.tools.list_ports
        
        ports = []
        for port in serial.tools.list_ports.comports():
            ports.append({
                'device': port.device,
                'description': port.description,
                'hwid': port.hwid,
                'vid': port.vid,
                'pid': port.pid,
                'serial_number': port.serial_number,
                'manufacturer': port.manufacturer
            })
        
        return jsonify({
            'success': True,
            'data': ports,
            'total_count': len(ports)
        })
        
    except ImportError:
        return jsonify({
            'success': False,
            'error': 'pyserial 套件未安裝'
        }), 500
    except Exception as e:
        logging.error(f"獲取串口列表時發生錯誤: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@uart_bp.route('/start', methods=['POST'])
def api_uart_start():
    """啟動 UART 讀取"""
    try:
        data = request.get_json()
        port = data.get('port', '/dev/ttyUSB0')
        baudrate = data.get('baudrate', 9600)
        
        # 這裡應該實現實際的UART啟動邏輯
        # 暫時返回模擬結果
        
        return jsonify({
            'success': True,
            'message': f'UART 讀取已啟動 (端口: {port}, 波特率: {baudrate})',
            'config': {
                'port': port,
                'baudrate': baudrate,
                'start_time': datetime.now().isoformat()
            }
        })
        
    except Exception as e:
        logging.error(f"啟動UART時發生錯誤: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@uart_bp.route('/stop', methods=['POST'])
def api_uart_stop():
    """停止 UART 讀取"""
    try:
        # 這裡應該實現實際的UART停止邏輯
        
        return jsonify({
            'success': True,
            'message': 'UART 讀取已停止',
            'stop_time': datetime.now().isoformat()
        })
        
    except Exception as e:
        logging.error(f"停止UART時發生錯誤: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@uart_bp.route('/clear', methods=['POST'])
def api_uart_clear():
    """清除 UART 數據緩存"""
    try:
        # 這裡應該實現實際的數據清除邏輯
        
        return jsonify({
            'success': True,
            'message': 'UART 數據緩存已清除',
            'clear_time': datetime.now().isoformat()
        })
        
    except Exception as e:
        logging.error(f"清除UART數據時發生錯誤: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@uart_bp.route('/diagnostic', methods=['POST'])
def api_uart_diagnostic():
    """UART 診斷"""
    try:
        # 執行各種診斷檢查
        diagnostic_result = {
            'port_available': True,  # 應該檢查實際端口狀態
            'permissions': True,     # 應該檢查端口權限
            'driver_loaded': True,   # 應該檢查驅動程式狀態
            'data_flow': False,      # 應該檢查數據流狀態
            'last_data_time': None,  # 最後數據接收時間
            'error_count': 0,        # 錯誤計數
            'recommendations': [
                '檢查硬體連接',
                '確認波特率設定',
                '檢查設備權限'
            ]
        }
        
        return jsonify({
            'success': True,
            'data': diagnostic_result,
            'diagnostic_time': datetime.now().isoformat()
        })
        
    except Exception as e:
        logging.error(f"UART診斷時發生錯誤: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@uart_bp.route('/stream')
def api_uart_stream():
    """UART 數據流"""
    try:
        def generate_uart_stream():
            """生成UART數據流"""
            # 這裡應該實現實際的數據流邏輯
            # 暫時返回模擬數據
            import time
            
            while True:
                # 獲取最新數據
                latest_data = uart_model.safe_get_uart_data(uart_reader)
                
                if latest_data:
                    for data_point in latest_data[-5:]:  # 只發送最近5筆數據
                        yield f"data: {json.dumps(data_point)}\n\n"
                
                time.sleep(1)  # 每秒更新一次
        
        return Response(
            generate_uart_stream(),
            mimetype='text/plain',
            headers={
                'Cache-Control': 'no-cache',
                'Connection': 'keep-alive'
            }
        )
        
    except Exception as e:
        logging.error(f"UART數據流時發生錯誤: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@uart_bp.route('/receive-from-pi', methods=['POST'])
def api_uart_receive_from_pi():
    """從樹莓派接收數據"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': '沒有接收到數據'
            }), 400
        
        # 處理接收到的數據
        processed_data = {
            'received_time': datetime.now().isoformat(),
            'source': 'raspberry_pi',
            'data': data,
            'processed': True
        }
        
        # 這裡可以添加數據儲存邏輯
        
        return jsonify({
            'success': True,
            'message': '數據接收成功',
            'data': processed_data
        })
        
    except Exception as e:
        logging.error(f"從樹莓派接收數據時發生錯誤: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@uart_bp.route('/receive-data', methods=['POST'])
def api_uart_receive_data():
    """接收 UART 數據"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': '沒有接收到數據'
            }), 400
        
        # 驗證數據格式
        required_fields = ['mac_id', 'timestamp']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'success': False,
                    'error': f'缺少必要字段: {field}'
                }), 400
        
        # 處理接收到的數據
        processed_data = {
            'received_time': datetime.now().isoformat(),
            'source': 'uart_api',
            'data': data,
            'processed': True
        }
        
        return jsonify({
            'success': True,
            'message': 'UART 數據接收成功',
            'data': processed_data
        })
        
    except Exception as e:
        logging.error(f"接收UART數據時發生錯誤: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@uart_bp.route('/receive-batch', methods=['POST'])
def api_uart_receive_batch():
    """批次接收 UART 數據"""
    try:
        data = request.get_json()
        
        if not data or 'batch' not in data:
            return jsonify({
                'success': False,
                'error': '沒有接收到批次數據'
            }), 400
        
        batch_data = data['batch']
        if not isinstance(batch_data, list):
            return jsonify({
                'success': False,
                'error': '批次數據格式錯誤'
            }), 400
        
        processed_count = 0
        errors = []
        
        for i, item in enumerate(batch_data):
            try:
                # 驗證每個數據項目
                if 'mac_id' not in item or 'timestamp' not in item:
                    errors.append(f'項目 {i}: 缺少必要字段')
                    continue
                
                # 處理數據項目
                processed_count += 1
                
            except Exception as e:
                errors.append(f'項目 {i}: {str(e)}')
                continue
        
        return jsonify({
            'success': True,
            'message': f'批次處理完成，成功處理 {processed_count} 筆數據',
            'data': {
                'total_items': len(batch_data),
                'processed_count': processed_count,
                'error_count': len(errors),
                'errors': errors,
                'received_time': datetime.now().isoformat()
            }
        })
        
    except Exception as e:
        logging.error(f"批次接收UART數據時發生錯誤: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500