import serial
import threading
import time
import json
import re
import os
import csv
from datetime import datetime
from config.config_manager import ConfigManager
import paho.mqtt.client as mqtt

# 導入資料庫管理器
try:
    from database_manager import db_manager
    DATABASE_AVAILABLE = True
    print("資料庫管理器載入成功")
except ImportError as e:
    print(f"警告: 資料庫管理器載入失敗: {e}")
    DATABASE_AVAILABLE = False
    db_manager = None

# 嘗試導入 pymodbus API
try:
    from pymodbus.server.sync import StartSerialServer, StartTcpServer
    from pymodbus.datastore import ModbusSequentialDataBlock, ModbusSlaveContext, ModbusServerContext
    MODBUS_AVAILABLE = True
except ImportError as e:
    print(f"警告: pymodbus 模組不可用，Modbus 功能將被禁用: {e}")
    MODBUS_AVAILABLE = False
    StartSerialServer = None
    StartTcpServer = None
    ModbusSequentialDataBlock = None
    ModbusSlaveContext = None
    ModbusServerContext = None

import logging

# 在 logging 導入後記錄成功資訊
if MODBUS_AVAILABLE:
    logging.info("成功載入 pymodbus 2.5.3 同步 API")

class UARTReader:
    def __init__(self):
        self.config_manager = ConfigManager()
        self.serial_connection = None
        self.is_running = False
        self.latest_data = []
        self.max_data_count = None  # 無限制保存資料
        self.lock = threading.Lock()
        # 初始化時載入歷史數據
        self.load_historical_data()
        
    def load_historical_data(self, days_back=7):
        """載入最近幾天的歷史數據到 latest_data"""
        try:
            from datetime import datetime, timedelta
            
            current_dir = os.path.dirname(os.path.abspath(__file__))
            history_dir = os.path.join(current_dir, 'History')
            
            if not os.path.exists(history_dir):
                logging.info("History 資料夾不存在，無法載入歷史數據")
                return
            
            # 計算要載入的日期範圍
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days_back)
            
            loaded_data = []
            
            # 掃描 History 資料夾中的 CSV 檔案
            for filename in os.listdir(history_dir):
                if filename.startswith('uart_data_') and filename.endswith('.csv'):
                    try:
                        # 從檔名提取日期
                        date_str = filename.replace('uart_data_', '').replace('.csv', '')
                        file_date = datetime.strptime(date_str, '%Y%m%d')
                        
                        # 只載入指定範圍內的數據
                        if start_date <= file_date <= end_date:
                            file_path = os.path.join(history_dir, filename)
                            
                            # 讀取 CSV 檔案
                            with open(file_path, 'r', encoding='utf-8') as f:
                                reader = csv.DictReader(f)
                                for row in reader:
                                    # 轉換為標準格式
                                    data_entry = {
                                        'timestamp': row.get('timestamp', ''),
                                        'mac_id': row.get('mac_id', 'N/A'),
                                        'channel': int(row.get('channel', 0)),
                                        'parameter': float(row.get('parameter', 0.0)),
                                        'unit': row.get('unit', 'N/A')
                                    }
                                    loaded_data.append(data_entry)
                                    
                            logging.info(f"載入歷史數據檔案: {filename}")
                            
                    except Exception as e:
                        logging.warning(f"載入檔案 {filename} 時發生錯誤: {e}")
                        continue
            
            # 按時間排序
            loaded_data.sort(key=lambda x: x.get('timestamp', ''))
            
            # 更新 latest_data
            with self.lock:
                self.latest_data = loaded_data
                
            logging.info(f"歷史數據載入完成，共載入 {len(loaded_data)} 筆數據")
            
            # 顯示載入的數據摘要
            if loaded_data:
                mac_ids = set(entry.get('mac_id') for entry in loaded_data)
                logging.info(f"載入的 MAC ID: {list(mac_ids)}")
                
        except Exception as e:
            logging.error(f"載入歷史數據時發生錯誤: {e}")
            
    def reload_historical_data(self):
        """重新載入歷史數據的公開方法"""
        self.load_historical_data()
        
    def get_uart_config(self):
        """從配置管理器獲取UART設定"""
        try:
            # 強制重新載入配置，確保使用最新設定
            self.config_manager.load_config()
            # 嘗試從配置管理器獲取UART設定
            uart_config = self.config_manager.get_protocol_config('UART')
            com_port = uart_config.get('com_port', '/dev/ttyUSB0')
            baud_rate = uart_config.get('baud_rate', 9600)
            parity = uart_config.get('parity', 'N')
            stopbits = uart_config.get('stopbits', 1)
            bytesize = uart_config.get('bytesize', 8)
            timeout = uart_config.get('timeout', 1)
            
        except Exception as e:
            logging.warning(f"載入UART配置失敗，使用預設值: {e}")
            # 如果沒有UART配置，使用Linux預設值
            com_port = '/dev/ttyUSB0'
            baud_rate = 9600
            parity = 'N'
            stopbits = 1
            bytesize = 8
            timeout = 1
            
        return com_port, baud_rate, parity, stopbits, bytesize, timeout
    
    def parse_uart_data(self, data_string):
        """解析UART資料字串，提取MAC ID、Channel、Parameter等資訊"""
        try:
            # 假設資料格式為: MAC_ID,Channel,Parameter 或其他格式
            # 這裡需要根據實際的資料格式進行調整
            
            # 範例解析邏輯（請根據實際資料格式調整）
            parts = data_string.strip().split(',')
            
            if len(parts) >= 3:
                import re
                mac_id = re.sub(r'^[^0-9A-Fa-f]+', '', parts[0].strip())
                channel_str = parts[1].strip()
                parameter_str = parts[2].strip()
                
                # 嘗試提取Channel數字
                channel_match = re.search(r'(\d+)', channel_str)
                channel = int(channel_match.group(1)) if channel_match else 0
                
                # 嘗試提取Parameter數值
                param_match = re.search(r'([+-]?\d*\.?\d+)', parameter_str)
                parameter = float(param_match.group(1)) if param_match else 0.0
                
                # 根據Channel判斷單位
                unit = 'A' if 0 <= channel <= 6 else 'V' if channel == 7 else 'N/A'
                
                logging.info(f"解析UART資料: {data_string} -> mac_id={mac_id}, channel={channel}, parameter={parameter}, unit={unit}")
                return {
                    'mac_id': mac_id,
                    'channel': channel,
                    'parameter': parameter,
                    'unit': unit
                }
            else:
                logging.warning(f"UART資料格式異常: {data_string}")
                # 如果無法解析，返回預設值
                return {
                    'mac_id': 'N/A',
                    'channel': 0,
                    'parameter': 0.0,
                    'unit': 'N/A'
                }
                
        except Exception as e:
            logging.exception(f"解析UART資料時發生錯誤: {str(e)}，原始資料: {data_string}")
            return {
                'mac_id': 'N/A',
                'channel': 0,
                'parameter': 0.0,
                'unit': 'N/A'
            }
    
    def test_uart_connection(self):
        """測試UART連接"""
        com_port, baud_rate, parity, stopbits, bytesize, timeout = self.get_uart_config()
        
        try:
            # 嘗試開啟串口
            test_serial = serial.Serial(
                port=com_port,
                baudrate=baud_rate,
                parity=parity,
                stopbits=stopbits,
                bytesize=bytesize,
                timeout=timeout
            )
            
            # 檢查串口是否開啟
            if test_serial.is_open:
                test_serial.close()
                return True, f"UART連接測試成功 - 埠口: {com_port}"
            else:
                return False, f"UART連接測試失敗 - 無法開啟埠口: {com_port}"
                
        except serial.SerialException as e:
            return False, f"串口錯誤: {str(e)}"
        except Exception as e:
            return False, f"UART測試失敗: {str(e)}"
    
    def list_available_ports(self):
        """列出可用的串口"""
        try:
            import serial.tools.list_ports
            ports = serial.tools.list_ports.comports()
            available_ports = []
            
            for port in ports:
                available_ports.append({
                    'device': port.device,
                    'description': port.description,
                    'hwid': port.hwid
                })
            
            return available_ports
        except Exception as e:
            logging.exception(f"列出串口時發生錯誤: {str(e)}")
            return []

    def start_reading(self):
        """開始讀取UART資料"""
        if self.is_running:
            return False
            
        com_port, baud_rate, parity, stopbits, bytesize, timeout = self.get_uart_config()
        
        try:
            self.serial_connection = serial.Serial(
                port=com_port,
                baudrate=baud_rate,
                parity=parity,
                stopbits=stopbits,
                bytesize=bytesize,
                timeout=timeout
            )
            self.is_running = True
            
            # 啟動讀取執行緒
            read_thread = threading.Thread(target=self._read_loop, daemon=True)
            read_thread.start()
            
            logging.info(f"UART 開始讀取 - 埠口: {com_port}, 波特率: {baud_rate}")
            return True
            
        except Exception as e:
            logging.exception(f"UART 連接失敗: {str(e)}")
            logging.error("=== UART 故障排除建議 ===")
            logging.error(f"1. 檢查串口設備是否存在: ls -la {com_port}")
            logging.error("2. 檢查可用的串口: ls -la /dev/ttyUSB* /dev/ttyACM*")
            logging.error("3. 檢查使用者權限: sudo usermod -a -G dialout $USER")
            logging.error("4. 重新載入 USB 串口驅動: sudo modprobe ftdi_sio")
            logging.error("5. 檢查 USB 設備: lsusb")
            logging.error("6. 檢查系統日誌: dmesg | tail")
            logging.error(f"目前嘗試的埠口: {com_port}")
            logging.error("==========================")
            return False
    
    def stop_reading(self):
        """停止讀取UART資料"""
        self.is_running = False
        if self.serial_connection:
            self.serial_connection.close()
            self.serial_connection = None
        logging.info("UART 讀取已停止")
    
    def start(self):
        """啟動UART讀取（與其他協定接收器保持一致的介面）"""
        return self.start_reading()
    
    def stop(self):
        """停止UART讀取（與其他協定接收器保持一致的介面）"""
        self.stop_reading()
    
    def _read_loop(self):
        """UART讀取迴圈"""
        while self.is_running:
            try:
                if self.serial_connection and self.serial_connection.is_open:
                    line = self.serial_connection.readline()
                    if line:
                        # 解碼資料
                        decoded_line = line.decode('utf-8', errors='ignore').strip()
                        if decoded_line:
                            # 解析資料
                            parsed_data = self.parse_uart_data(decoded_line)
                            
                            # 建立資料物件
                            data_entry = {
                                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                                'data': decoded_line,
                                'raw': line.hex(),
                                'mac_id': parsed_data['mac_id'],
                                'channel': parsed_data['channel'],
                                'parameter': parsed_data['parameter'],
                                'unit': parsed_data['unit']
                            }
                            
                            # 更新最新資料
                            with self.lock:
                                self.latest_data.append(data_entry)
                                
                                # 自動清理超過30分鐘的舊數據
                                self._cleanup_old_data()
                            
                            logging.info(f"UART 收到: {decoded_line} -> {data_entry}")
                            
                            # 儲存到資料庫
                            if DATABASE_AVAILABLE and db_manager:
                                try:
                                    # 準備資料庫格式的資料
                                    db_data = {
                                        'timestamp': data_entry['timestamp'],
                                        'mac_id': data_entry['mac_id'],
                                        'raw_data': decoded_line,
                                        'device_type': 'UART Device',  # 可以從配置中取得
                                        'device_model': 'Unknown',      # 可以從配置中取得
                                        'factory_area': 'Default',      # 可以從配置中取得
                                        'floor_level': 'Default',       # 可以從配置中取得
                                        'status': 'normal'
                                    }
                                    
                                    # 根據 channel 和 unit 設定對應的感測器數據
                                    if parsed_data['unit'] == 'A':
                                        db_data['current'] = parsed_data['parameter']
                                    elif parsed_data['unit'] == 'V':
                                        db_data['voltage'] = parsed_data['parameter']
                                    elif parsed_data['channel'] == 0:  # 假設 channel 0 是溫度
                                        db_data['temperature'] = parsed_data['parameter']
                                    elif parsed_data['channel'] == 1:  # 假設 channel 1 是濕度
                                        db_data['humidity'] = parsed_data['parameter']
                                    
                                    # 儲存到資料庫
                                    success = db_manager.save_uart_data(db_data)
                                    if success:
                                        logging.debug(f"資料成功儲存到資料庫: MAC={data_entry['mac_id']}")
                                    else:
                                        logging.warning(f"資料儲存到資料庫失敗: MAC={data_entry['mac_id']}")
                                        
                                except Exception as db_e:
                                    logging.error(f"資料庫儲存錯誤: {db_e}")
                            
                            # 離線模式：將資料保存到本地History資料夾
                            self._save_to_local_history(data_entry)
                            
                            # 若目前協定為MQTT，則發佈資料
                            try:
                                from uart_integrated import protocol_manager
                                if getattr(protocol_manager, 'active', None) == 'MQTT':
                                    try:
                                        self.config_manager.load_config()
                                        mqtt_receiver = protocol_manager.protocols['MQTT']
                                        if mqtt_receiver.is_running:  # 確保MQTT連接正常
                                            config = self.config_manager.get_protocol_config('MQTT')
                                            mqtt_payload = {
                                                "timestamp": data_entry["timestamp"],
                                                "mac_id": data_entry["mac_id"],
                                                "channel": data_entry["channel"],
                                                "parameter": data_entry["parameter"],
                                                "unit": data_entry["unit"]
                                            }
                                            mqtt_receiver.publish(config['topic'], json.dumps(mqtt_payload, ensure_ascii=False))
                                            logging.info(f"UART->MQTT 發佈: topic={config['topic']}, payload={mqtt_payload}")
                                        else:
                                            logging.warning("MQTT接收器未運行，跳過發佈")
                                    except Exception as mqtt_e:
                                        logging.warning(f"MQTT發佈失敗（可能因為沒有網路連接）: {mqtt_e}")
                                # 若目前協定為RTU，則寫入register
                                elif getattr(protocol_manager, 'active', None) == 'RTU':
                                    protocol_manager.protocols['RTU'].update_registers(data_entry)
                                    logging.info(f"UART->RTU 更新register: {data_entry}")
                                # 若目前協定為TCP，則寫入TCP register
                                elif getattr(protocol_manager, 'active', None) == 'TCP':
                                    protocol_manager.protocols['TCP'].update_registers(data_entry)
                                    logging.info(f"UART->TCP 更新register: {data_entry}")
                                # 若目前協定為FTP，則新增資料到上傳佇列
                                elif getattr(protocol_manager, 'active', None) == 'FTP':
                                    protocol_manager.protocols['FTP'].add_data(data_entry)
                                    logging.info(f"UART->FTP 新增上傳資料: {data_entry}")
                            except Exception as e:
                                logging.warning(f"[UART->協定] 發佈/寫入失敗（可能因為沒有網路連接）: {e}")
                time.sleep(0.1)  # 短暫休息避免CPU過度使用
                
            except Exception as e:
                logging.exception(f"UART 讀取錯誤: {str(e)}")
                time.sleep(1)  # 錯誤時等待較長時間
    
    def get_latest_data(self):
        """獲取最新的UART資料"""
        with self.lock:
            return self.latest_data.copy()
    
    def get_data_count(self):
        """獲取資料筆數"""
        with self.lock:
            return len(self.latest_data)
    
    def clear_data(self):
        """清除所有資料"""
        with self.lock:
            self.latest_data.clear()
    
    def get_status(self):
        """獲取UART讀取器狀態"""
        try:
            com_port, baud_rate, parity, stopbits, bytesize, timeout = self.get_uart_config()
            
            status = {
                'status': 'running' if self.is_running else 'stopped',
                'is_running': self.is_running,
                'port': com_port,
                'baud_rate': baud_rate,
                'parity': parity,
                'stopbits': stopbits,
                'bytesize': bytesize,
                'timeout': timeout,
                'data_count': self.get_data_count(),
                'connected': self.serial_connection is not None and self.serial_connection.is_open if self.serial_connection else False,
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            return status
            
        except Exception as e:
            logging.error(f"獲取UART狀態時發生錯誤: {e}")
            return {
                'status': 'error',
                'is_running': False,
                'error': str(e),
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
    
    def _cleanup_old_data(self):
        """清理超過2小時的舊數據（修正：延長保留時間以確保 MAC ID 不會過快消失）"""
        try:
            from datetime import datetime, timedelta
            # 修正：從30分鐘改為2小時，確保 MAC ID 有足夠時間被前端獲取
            two_hours_ago = datetime.now() - timedelta(hours=2)
            
            # 計算清理前的數據量
            original_count = len(self.latest_data)
            
            # 過濾出2小時內的數據
            filtered_data = []
            for entry in self.latest_data:
                try:
                    # 解析時間戳
                    entry_timestamp = datetime.strptime(entry['timestamp'], '%Y-%m-%d %H:%M:%S')
                    if entry_timestamp >= two_hours_ago:
                        filtered_data.append(entry)
                except ValueError:
                    # 如果時間戳解析失敗，保留該數據
                    filtered_data.append(entry)
            
            # 更新數據列表
            self.latest_data = filtered_data
            
            # 記錄清理結果
            cleaned_count = original_count - len(filtered_data)
            if cleaned_count > 0:
                logging.info(f"UART數據自動清理: 移除 {cleaned_count} 筆超過2小時的舊數據，剩餘 {len(filtered_data)} 筆")
                
        except Exception as e:
            logging.warning(f"清理舊數據時發生錯誤: {e}")
    
    def _save_to_local_history(self, data_entry):
        """將資料保存到本地History資料夾，依照日期分類"""
        try:
            # 動態獲取當前執行程式的目錄
            current_dir = os.path.dirname(os.path.abspath(__file__))
            
            # 建立History資料夾路徑
            history_dir = os.path.join(current_dir, 'History')
            
            # 檢查History資料夾是否存在，如果不存在就建立
            if not os.path.exists(history_dir):
                os.makedirs(history_dir)
                logging.info(f"建立History資料夾: {history_dir}")
            
            # 根據日期建立檔案名稱
            date_str = datetime.now().strftime('%Y%m%d')
            filename = f"uart_data_{date_str}.csv"
            file_path = os.path.join(history_dir, filename)
            
            # 檢查檔案是否存在，決定是否需要寫入標題行
            file_exists = os.path.exists(file_path)
            
            # 寫入資料到CSV檔案
            with open(file_path, 'a', newline='', encoding='utf-8') as csvfile:
                fieldnames = ['timestamp', 'mac_id', 'channel', 'parameter', 'unit']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                
                # 如果檔案不存在，先寫入標題行
                if not file_exists:
                    writer.writeheader()
                    logging.info(f"建立新的資料檔案: {file_path}")
                
                # 只寫入解析後的結構化資料，不包含原始data和raw
                csv_data = {
                    'timestamp': data_entry['timestamp'],
                    'mac_id': data_entry['mac_id'],
                    'channel': data_entry['channel'],
                    'parameter': data_entry['parameter'],
                    'unit': data_entry['unit']
                }
                writer.writerow(csv_data)
                
            logging.info(f"資料已保存到本地: {file_path}")
            
        except Exception as e:
            logging.exception(f"保存資料到本地History資料夾失敗: {e}")
    


# --- 新增各通訊協定接收器骨架 ---
class MQTTReceiver:
    def __init__(self, config_manager):
        self.config_manager = config_manager
        self.is_running = False
        self.client = None
        self.latest_data = []
    def start(self):
        try:
            self.config_manager.load_config()
            config = self.config_manager.get_protocol_config('MQTT')
            self.client = mqtt.Client()
            self.client.on_connect = self.on_connect
            self.client.on_message = self.on_message
            
            # 設定連接超時，避免無網路時長時間等待
            self.client.socket_timeout = 5
            self.client.socket_keepalive = 60
            
            try:
                self.client.connect(config['broker'], config['port'], 60)
                self.client.loop_start()
                self.is_running = True
                logging.info(f"[MQTT] 啟動MQTT接收器，連線到 {config['broker']}:{config['port']}，訂閱 {config['topic']}")
            except Exception as e:
                logging.warning(f"[MQTT] 連線失敗（可能因為沒有網路連接）: {e}")
                self.is_running = False
        except Exception as e:
            logging.warning(f"[MQTT] 啟動失敗: {e}")
            self.is_running = False
    def stop(self):
        if self.client:
            self.client.loop_stop()
            self.client.disconnect()
        self.is_running = False
        logging.info("[MQTT] 停止MQTT接收器")
    def on_connect(self, client, userdata, flags, rc):
        logging.info(f"[MQTT] 連線結果: {rc}")
        # 重新載入配置確保使用最新設定
        self.config_manager.load_config()
        config = self.config_manager.get_protocol_config('MQTT')
        client.subscribe(config['topic'])
        logging.info(f"[MQTT] 已訂閱: {config['topic']}")
    def on_message(self, client, userdata, msg):
        payload = msg.payload.decode('utf-8', errors='ignore')
        logging.info(f"[MQTT] 收到訊息: {msg.topic} | 內容: {payload}")
        self.latest_data.append({
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'topic': msg.topic,
            'payload': payload
        })
        if len(self.latest_data) > 100:
            self.latest_data = self.latest_data[-100:]
    def get_latest_data(self):
        return self.latest_data.copy()
    def publish(self, topic, payload):
        if self.client and self.is_running:
            self.client.publish(topic, payload)
            logging.info(f"[MQTT] 發佈訊息到 {topic} | 內容: {payload}")

class TCPReceiver:
    def __init__(self, config_manager):
        self.config_manager = config_manager
        self.is_running = False
        self.device_register_map = {}  # MAC: 起始register index
        self.next_base = 101  # 第一台設備從101開始
        self.register_block_size = 12  # 4(MAC)+8(channel)
        self.max_devices = 10
        self.lock = threading.Lock()
        self.server_instance = None  # 保存服務器實例
        
        if MODBUS_AVAILABLE:
            self.store = ModbusSlaveContext(
                hr=ModbusSequentialDataBlock(0, [0]*1000)  # 1000個holding register
            )
            self.context = ModbusServerContext(slaves=self.store, single=True)
        else:
            self.store = None
            self.context = None
            logging.warning("Modbus 功能不可用，TCP協定將被禁用")
            
        self.server_thread = None
        
    def _check_port_available(self, host, port):
        """檢查端口是否可用"""
        import socket
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex((host, port))
            sock.close()
            return result != 0  # 如果連接失敗，表示端口可用
        except Exception as e:
            logging.warning(f"[TCP] 檢查端口時發生錯誤: {e}")
            return False
            
    def _find_available_port(self, host, start_port, max_attempts=10):
        """尋找可用的端口"""
        for i in range(max_attempts):
            port = start_port + i
            if self._check_port_available(host, port):
                return port
        return None
        
    def start(self):
        if self.is_running:
            logging.warning("[TCP] TCP接收器已在運行中")
            return
            
        if not MODBUS_AVAILABLE:
            logging.error("[TCP] 無法啟動TCP服務：pymodbus 模組不可用")
            return
            
        # 強制重新載入配置，確保使用最新設定
        self.config_manager.load_config()
        config = self.config_manager.get_protocol_config('TCP')
        tcp_host = config.get('host', '0.0.0.0')
        tcp_port = config.get('port', 5020)  # 改用 5020 作為預設端口
        
        # 檢查端口是否可用
        if not self._check_port_available(tcp_host, tcp_port):
            logging.warning(f"[TCP] 端口 {tcp_port} 已被占用，嘗試尋找可用端口...")
            available_port = self._find_available_port(tcp_host, tcp_port)
            if available_port:
                tcp_port = available_port
                logging.info(f"[TCP] 使用替代端口: {tcp_port}")
                # 更新配置中的端口
                config['port'] = tcp_port
                self.config_manager.update_protocol_config('TCP', config)
            else:
                logging.error(f"[TCP] 無法找到可用端口，啟動失敗")
                return
        
        self.is_running = True
        
        def run_server():
            try:
                # 嘗試啟動服務器
                logging.info(f"[TCP] 正在啟動 TCP 服務器於 {tcp_host}:{tcp_port}...")
                
                # 使用 pymodbus 2.5.3 同步 API
                StartTcpServer(
                    context=self.context, 
                    address=(tcp_host, tcp_port)
                )
                    
                logging.info(f"[TCP] TCP伺服器啟動成功，host={tcp_host}, port={tcp_port}")
                
            except OSError as os_error:
                if "10048" in str(os_error) or "Address already in use" in str(os_error):
                    logging.error(f"[TCP] 端口 {tcp_port} 被占用: {os_error}")
                    logging.error(f"[TCP] 請檢查是否有其他程序在使用此端口，或重新啟動應用程式")
                    
                    # 嘗試釋放端口並重試
                    self._cleanup_port(tcp_host, tcp_port)
                    
                else:
                    logging.error(f"[TCP] 網路錯誤: {os_error}")
                    
                self.is_running = False
                
            except Exception as e:
                logging.exception(f"[TCP] Server啟動失敗: {e}")
                self.is_running = False
                
            except Exception as e:
                logging.exception(f"[TCP] Server啟動失敗: {e}")
                self.is_running = False
                
        self.server_thread = threading.Thread(target=run_server, daemon=True)
        self.server_thread.start()
        logging.info(f"[TCP] 啟動TCP接收器，host={tcp_host}, port={tcp_port}")
        
    def _cleanup_port(self, host, port):
        """嘗試清理占用的端口"""
        try:
            import socket
            import time
            
            logging.info(f"[TCP] 嘗試清理端口 {port}...")
            
            # 創建socket並設置SO_REUSEADDR
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            
            try:
                sock.bind((host, port))
                sock.close()
                logging.info(f"[TCP] 端口 {port} 清理成功")
                time.sleep(1)  # 等待端口完全釋放
            except Exception as e:
                logging.warning(f"[TCP] 無法清理端口 {port}: {e}")
            finally:
                try:
                    sock.close()
                except:
                    pass
                    
        except Exception as e:
            logging.warning(f"[TCP] 清理端口時發生錯誤: {e}")
            
    def stop(self):
        """停止TCP服務器"""
        self.is_running = False
        
        # 嘗試關閉服務器實例
        if self.server_instance:
            try:
                if hasattr(self.server_instance, 'shutdown'):
                    self.server_instance.shutdown()
                elif hasattr(self.server_instance, 'server_close'):
                    self.server_instance.server_close()
                logging.info("[TCP] TCP服務器已關閉")
            except Exception as e:
                logging.warning(f"[TCP] 關閉服務器時發生錯誤: {e}")
            finally:
                self.server_instance = None
        
        # 等待服務器線程結束
        if self.server_thread and self.server_thread.is_alive():
            try:
                self.server_thread.join(timeout=5)
                if self.server_thread.is_alive():
                    logging.warning("[TCP] 服務器線程未能正常結束")
            except Exception as e:
                logging.warning(f"[TCP] 等待服務器線程結束時發生錯誤: {e}")
        
        logging.info("[TCP] 停止TCP接收器")
        
    def get_latest_data(self):
        if self.store:
            return self.store.getValues(3, 0, 1000)
        return []
        
    def update_registers(self, data_entry):
        mac = data_entry.get('mac_id', '')
        channel = data_entry.get('channel', 0)
        parameter = data_entry.get('parameter', 0)
        if not mac or not isinstance(channel, int):
            return
        with self.lock:
            if mac not in self.device_register_map:
                if len(self.device_register_map) >= self.max_devices:
                    logging.warning(f"[TCP] 超過最大設備數，無法分配register: {mac}")
                    return
                base = self.next_base
                self.device_register_map[mac] = base
                self.next_base += 100
                try:
                    mac_hex = mac.ljust(16, '0')[:16]
                    mac_parts = [int(mac_hex[i:i+4], 16) for i in range(0, 16, 4)]
                    for i, val in enumerate(mac_parts):
                        self.store.setValues(3, base + i, [val])
                    logging.info(f"[TCP] MAC寫入: {mac} -> {mac_parts}")
                except Exception as e:
                    logging.exception(f"[TCP] MAC寫入失敗: {e}")
            else:
                base = self.device_register_map[mac]
            if 0 <= channel <= 7:
                reg_addr = base + 4 + channel
                try:
                    reg_val = int(float(parameter) * 100)
                    self.store.setValues(3, reg_addr, [reg_val])
                    logging.info(f"[TCP] channel寫入: mac={mac}, channel={channel}, value={reg_val}")
                except Exception as e:
                    logging.exception(f"[TCP] channel寫入失敗: {e}")
        logging.info(f"目前register內容：{self.store.getValues(3, 0, 120)}")

class FTPReceiver:
    def __init__(self, config_manager):
        self.config_manager = config_manager
        self.is_running = False
        self.ftp_connection = None
        self.latest_data = []
        self.max_data_count = None  # 無限制保存資料
        self.lock = threading.Lock()
        self.upload_interval = 30  # 每30秒上傳一次
        self.last_upload_time = 0
        self.upload_thread = None
        
    def start(self):
        if self.is_running:
            return
        self.is_running = True
        # 啟動上傳執行緒
        self.upload_thread = threading.Thread(target=self._upload_loop, daemon=True)
        self.upload_thread.start()
        logging.info("[FTP] 啟動FTP接收器")
        
    def stop(self):
        self.is_running = False
        if self.ftp_connection:
            try:
                self.ftp_connection.quit()
            except Exception as e:
                logging.exception(f"[FTP] 關閉FTP連線失敗: {e}")
            self.ftp_connection = None
        logging.info("[FTP] 停止FTP接收器")
        
    def get_latest_data(self):
        with self.lock:
            return self.latest_data.copy()
            
    def add_data(self, data_entry):
        """新增資料到FTP佇列"""
        with self.lock:
            self.latest_data.append(data_entry)
            logging.info(f"[FTP] 新增上傳資料: {data_entry}")
                
    def _upload_loop(self):
        """FTP上傳迴圈"""
        while self.is_running:
            try:
                current_time = time.time()
                if current_time - self.last_upload_time >= self.upload_interval:
                    self._upload_data()
                    self.last_upload_time = current_time
                time.sleep(5)  # 每5秒檢查一次
            except Exception as e:
                logging.exception(f"[FTP] 上傳迴圈錯誤: {e}")
                time.sleep(10)
                
    def _upload_data(self):
        """上傳資料到FTP伺服器（同一天資料堆疊在CT_Data/ct_data_YYYYMMDD.csv）"""
        try:
            # 強制重新載入配置，確保使用最新設定
            self.config_manager.load_config()
            config = self.config_manager.get_protocol_config('FTP')
            host = config.get('host', 'localhost')
            port = config.get('port', 21)
            username = config.get('username', '')
            password = config.get('password', '')
            remote_dir = config.get('remote_dir', '/')
            passive_mode = config.get('passive_mode', True)
            
            # 檢查是否有資料需要上傳
            with self.lock:
                if not self.latest_data:
                    return
                data_to_upload = self.latest_data.copy()
                self.latest_data = []  # 清空已上傳的資料
            
            from ftplib import FTP, error_perm
            import io
            import csv
            from datetime import datetime
            
            # 建立FTP連接
            self.ftp_connection = FTP()
            self.ftp_connection.connect(host, port, timeout=30)
            self.ftp_connection.login(username, password)
            if passive_mode:
                self.ftp_connection.set_pasv(True)
            
            # 切換到遠端目錄，並確保CT_Data子目錄存在
            try:
                self.ftp_connection.cwd(remote_dir)
            except Exception as e:
                logging.exception(f"[FTP] 無法切換到目錄: {remote_dir}, 錯誤: {e}")
                return
            try:
                self.ftp_connection.cwd('CT_Data')
            except error_perm as e:
                if not str(e).startswith('550'):
                    logging.exception(f"[FTP] 下載舊檔案失敗: {e}")
                    return
                try:
                    self.ftp_connection.mkd('CT_Data')
                    self.ftp_connection.cwd('CT_Data')
                except Exception as e:
                    logging.exception(f"[FTP] 建立CT_Data資料夾失敗: {e}")
                    return
            except Exception as e:
                logging.exception(f"[FTP] 切換CT_Data資料夾失敗: {e}")
                return
            
            # 生成檔案名稱（只用日期）
            date_str = datetime.now().strftime('%Y%m%d')
            filename = f"ct_data_{date_str}.csv"
            
            # 下載舊檔案內容（如有）
            existing_rows = []
            file_exists = False
            try:
                buf = io.BytesIO()
                self.ftp_connection.retrbinary(f'RETR {filename}', buf.write)
                buf.seek(0)
                reader = csv.reader(io.StringIO(buf.getvalue().decode('utf-8')))
                for row in reader:
                    existing_rows.append(row)
                file_exists = True
            except error_perm as e:
                # 檔案不存在時會出現550錯誤，忽略即可
                if not str(e).startswith('550'):
                    logging.exception(f"[FTP] 下載舊檔案失敗: {e}")
                    return
            except Exception as e:
                logging.exception(f"[FTP] 下載舊檔案失敗: {e}")
                return
            
            # 準備合併內容
            output = io.StringIO()
            writer = csv.writer(output)
            # 如果是新檔案，寫入標題
            if not file_exists or not existing_rows:
                writer.writerow(['timestamp', 'mac_id', 'channel', 'parameter', 'unit'])
            else:
                # 寫入舊內容（全部）
                for row in existing_rows:
                    writer.writerow(row)
            # 寫入新資料
            for entry in data_to_upload:
                writer.writerow([
                    entry.get('timestamp', ''),
                    entry.get('mac_id', ''),
                    entry.get('channel', ''),
                    entry.get('parameter', ''),
                    entry.get('unit', '')
                ])
            csv_data = output.getvalue().encode('utf-8')
            data_stream = io.BytesIO(csv_data)
            
            # 覆蓋上傳
            self.ftp_connection.storbinary(f'STOR {filename}', data_stream)
            logging.info(f"[FTP] 成功堆疊上傳 {len(data_to_upload)} 筆資料到 CT_Data/{filename}")
            
            # 關閉連接
            self.ftp_connection.quit()
            self.ftp_connection = None
            
        except Exception as e:
            logging.exception(f"[FTP] 上傳失敗: {e}")
            if self.ftp_connection:
                try:
                    self.ftp_connection.quit()
                except:
                    pass
                self.ftp_connection = None

class FastAPIReceiver:
    def __init__(self, config_manager):
        self.config_manager = config_manager
        self.is_running = False
    def start(self):
        # 強制重新載入配置，確保使用最新設定
        self.config_manager.load_config()
        config = self.config_manager.get_protocol_config('FastAPI')
        self.is_running = True
        logging.info(f"[FastAPI] 啟動FastAPI接收器，配置: {config}（詳細實作待完成）")
    def stop(self):
        self.is_running = False
        logging.info("[FastAPI] 停止FastAPI接收器")
    def get_latest_data(self):
        return []

class RTUReceiver:
    def __init__(self, config_manager):
        self.config_manager = config_manager
        self.is_running = False
        self.device_register_map = {}  # MAC: 起始register index
        self.next_base = 101  # 第一台設備從101開始
        self.register_block_size = 12  # 4(MAC)+8(channel)
        self.max_devices = 10
        self.lock = threading.Lock()
        
        if MODBUS_AVAILABLE:
            self.store = ModbusSlaveContext(
                hr=ModbusSequentialDataBlock(0, [0]*1000)  # 1000個holding register
            )
            self.context = ModbusServerContext(slaves=self.store, single=True)
        else:
            self.store = None
            self.context = None
            logging.warning("Modbus 功能不可用，RTU協定將被禁用")
            
        self.server_thread = None
        self.server_params = None
    def start(self):
        if self.is_running:
            return
            
        if not MODBUS_AVAILABLE:
            logging.error("[RTU] 無法啟動RTU服務：pymodbus 模組不可用")
            return
            
        self.is_running = True
        # 強制reload config，確保抓到最新設定
        self.config_manager.load_config()
        config = self.config_manager.get_protocol_config('RTU')
        com_port = config.get('com_port', '/dev/ttyUSB1')
        baud_rate = int(config.get('baud_rate', 9600))
        parity = config.get('parity', 'N')
        stopbits = int(config.get('stopbits', 1))
        bytesize = int(config.get('bytesize', 8))
        self.server_params = (com_port, baud_rate, parity, stopbits, bytesize)
        def run_server():
            try:
                # 使用 pymodbus 2.5.3 同步 API
                StartSerialServer(
                    self.context, 
                    port=com_port, 
                    baudrate=baud_rate, 
                    parity=parity, 
                    stopbits=stopbits, 
                    bytesize=bytesize, 
                    method='rtu'
                )
                        
                logging.info(f"[RTU] Server啟動成功，port={com_port}, baudrate={baud_rate}")
            except Exception as e:
                logging.exception(f"[RTU] Server啟動失敗: {e}")
                self.is_running = False
        self.server_thread = threading.Thread(target=run_server, daemon=True)
        self.server_thread.start()
        logging.info(f"[RTU] 啟動RTU接收器，port={com_port}, baudrate={baud_rate}")
    def stop(self):
        self.is_running = False
        logging.info("[RTU] 停止RTU接收器")
    def get_latest_data(self):
        # 回傳所有設備的register內容
        return self.store.getValues(3, 0, count=1000)
    def update_registers(self, data_entry):
        # data_entry: {'mac_id':..., 'channel':..., 'parameter':...}
        mac = data_entry.get('mac_id', '')
        channel = data_entry.get('channel', 0)
        parameter = data_entry.get('parameter', 0)
        if not mac or not isinstance(channel, int):
            return
        with self.lock:
            # 分配register區塊
            if mac not in self.device_register_map:
                if len(self.device_register_map) >= self.max_devices:
                    logging.warning(f"[RTU] 超過最大設備數，無法分配register: {mac}")
                    return
                base = self.next_base
                self.device_register_map[mac] = base
                self.next_base += 100  # 每台設備預留100個register
                # 寫入MAC
                try:
                    mac_hex = mac.ljust(16, '0')[:16]
                    mac_parts = [int(mac_hex[i:i+4], 16) for i in range(0, 16, 4)]
                    for i, val in enumerate(mac_parts):
                        self.store.setValues(3, base + i, [val])
                    logging.info(f"[RTU] MAC寫入: {mac} -> {mac_parts}")
                except Exception as e:
                    logging.exception(f"[RTU] MAC寫入失敗: {e}")
            else:
                base = self.device_register_map[mac]
            # channel值寫入105~112（base+4~base+11）
            if 0 <= channel <= 7:
                reg_addr = base + 4 + channel
                try:
                    # 只存整數，浮點數*100
                    reg_val = int(float(parameter) * 100)
                    self.store.setValues(3, reg_addr, [reg_val])
                    logging.info(f"[RTU] channel寫入: mac={mac}, channel={channel}, value={reg_val}")
                except Exception as e:
                    logging.exception(f"[RTU] channel寫入失敗: {e}")
        # debug: 印出前120個register內容
        logging.info(f"目前register內容：{self.store.getValues(3, 0, 120)}")

uart_reader = UARTReader()  # 不自動啟動讀取，僅建立實例


# --- 協定管理器 ---
class ProtocolManager:
    def __init__(self):
        self.config_manager = ConfigManager()
        self.protocols = {
            'UART': uart_reader,
            'MQTT': MQTTReceiver(self.config_manager),
            'TCP': TCPReceiver(self.config_manager),
            'FTP': FTPReceiver(self.config_manager),
            'FastAPI': FastAPIReceiver(self.config_manager),
            'RTU': RTUReceiver(self.config_manager)
        }
        self.active = None
        self.last_error = None
        
    def start(self, protocol):
        """啟動指定協定，包含錯誤處理和端口管理"""
        try:
            # 記錄啟動嘗試
            logging.info(f"[ProtocolManager] 嘗試啟動協定: {protocol}")
            
            # 檢查協定是否支援
            if protocol not in self.protocols:
                error_msg = f"不支援的協定: {protocol}"
                logging.warning(f"[ProtocolManager] {error_msg}")
                self.last_error = error_msg
                return False
            
            # 停止其他協定
            self._stop_all_protocols(exclude=protocol)
            
            # 特殊處理需要端口的協定
            if protocol in ['TCP', 'RTU']:
                if not self._check_and_prepare_port(protocol):
                    return False
            
            # 啟動指定協定
            try:
                self.protocols[protocol].start()
                
                # 驗證啟動是否成功
                import time
                time.sleep(1)  # 等待一秒讓服務完全啟動
                
                if hasattr(self.protocols[protocol], 'is_running'):
                    if not self.protocols[protocol].is_running:
                        error_msg = f"{protocol} 協定啟動失敗 - is_running = False"
                        logging.error(f"[ProtocolManager] {error_msg}")
                        self.last_error = error_msg
                        return False
                
                self.active = protocol
                self.last_error = None
                logging.info(f"[ProtocolManager] 成功啟用協定: {protocol}")
                return True
                
            except Exception as e:
                error_msg = f"啟動 {protocol} 協定時發生錯誤: {str(e)}"
                logging.exception(f"[ProtocolManager] {error_msg}")
                self.last_error = error_msg
                return False
                
        except Exception as e:
            error_msg = f"協定管理器啟動 {protocol} 時發生未預期錯誤: {str(e)}"
            logging.exception(f"[ProtocolManager] {error_msg}")
            self.last_error = error_msg
            return False
    
    def _stop_all_protocols(self, exclude=None):
        """停止所有協定，可排除指定協定"""
        for name, receiver in self.protocols.items():
            if name != exclude and hasattr(receiver, 'stop'):
                try:
                    receiver.stop()
                    logging.info(f"[ProtocolManager] 已停止協定: {name}")
                except Exception as e:
                    logging.warning(f"[ProtocolManager] 停止協定 {name} 時發生錯誤: {e}")
    
    def _check_and_prepare_port(self, protocol):
        """檢查和準備協定所需的端口"""
        try:
            config = self.config_manager.get_protocol_config(protocol)
            
            if protocol == 'TCP':
                host = config.get('host', '0.0.0.0')
                port = config.get('port', 5020)
                
                # 檢查端口是否可用
                from port_manager import PortManager
                
                if not PortManager.check_port_available(host, port):
                    logging.warning(f"[ProtocolManager] TCP 端口 {host}:{port} 被占用，嘗試清理...")
                    
                    # 嘗試清理端口
                    if PortManager.cleanup_port(host, port):
                        logging.info(f"[ProtocolManager] TCP 端口 {port} 清理成功")
                    else:
                        # 尋找替代端口
                        alternative_port = PortManager.find_available_port(host, port)
                        if alternative_port:
                            logging.info(f"[ProtocolManager] 使用替代 TCP 端口: {alternative_port}")
                            config['port'] = alternative_port
                            self.config_manager.update_protocol_config(protocol, config)
                        else:
                            error_msg = f"TCP 協定無法找到可用端口（從 {port} 開始）"
                            logging.error(f"[ProtocolManager] {error_msg}")
                            self.last_error = error_msg
                            return False
            
            elif protocol == 'RTU':
                com_port = config.get('com_port', '/dev/ttyUSB1')
                
                # 檢查串口是否可用
                try:
                    import serial
                    test_serial = serial.Serial(com_port, timeout=0.1)
                    test_serial.close()
                    logging.info(f"[ProtocolManager] RTU 串口 {com_port} 可用")
                except Exception as e:
                    error_msg = f"RTU 串口 {com_port} 不可用: {str(e)}"
                    logging.error(f"[ProtocolManager] {error_msg}")
                    self.last_error = error_msg
                    return False
            
            return True
            
        except Exception as e:
            error_msg = f"檢查 {protocol} 協定端口時發生錯誤: {str(e)}"
            logging.exception(f"[ProtocolManager] {error_msg}")
            self.last_error = error_msg
            return False
    
    def stop(self, protocol=None):
        """停止指定協定或所有協定"""
        try:
            if protocol:
                if protocol in self.protocols and hasattr(self.protocols[protocol], 'stop'):
                    self.protocols[protocol].stop()
                    if self.active == protocol:
                        self.active = None
                    logging.info(f"[ProtocolManager] 已停止協定: {protocol}")
            else:
                self._stop_all_protocols()
                self.active = None
                logging.info("[ProtocolManager] 已停止所有協定")
                
        except Exception as e:
            logging.exception(f"[ProtocolManager] 停止協定時發生錯誤: {e}")
    
    def get_status(self):
        """獲取協定管理器狀態"""
        status = {
            'active_protocol': self.active,
            'last_error': self.last_error,
            'protocols': {}
        }
        
        for name, receiver in self.protocols.items():
            try:
                if hasattr(receiver, 'get_status'):
                    protocol_status = receiver.get_status()
                elif hasattr(receiver, 'is_running'):
                    protocol_status = {
                        'is_running': receiver.is_running,
                        'status': 'running' if receiver.is_running else 'stopped'
                    }
                else:
                    protocol_status = {'status': 'unknown'}
                    
                status['protocols'][name] = protocol_status
                
            except Exception as e:
                status['protocols'][name] = {
                    'status': 'error',
                    'error': str(e)
                }
        
        return status
    
    def get_latest_data(self):
        """獲取目前啟用協定的最新資料"""
        try:
            if self.active and self.active in self.protocols:
                return self.protocols[self.active].get_latest_data()
            return []
        except Exception as e:
            logging.warning(f"[ProtocolManager] 獲取資料時發生錯誤: {e}")
            return []
    
    def get_last_error(self):
        """獲取最後的錯誤訊息"""
        return self.last_error

# 全域協定管理器實例
protocol_manager = ProtocolManager()

