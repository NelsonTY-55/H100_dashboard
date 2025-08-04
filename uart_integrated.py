import serial
import threading
import time
import json
import re
import os
import csv
from datetime import datetime
from config_manager import ConfigManager
import paho.mqtt.client as mqtt

# 嘗試導入新版pymodbus API，如果失敗則使用舊版或跳過
try:
    from pymodbus.server import StartSerialServer, StartTcpServer
    from pymodbus.datastore import ModbusSequentialDataBlock, ModbusSlaveContext, ModbusServerContext
    MODBUS_AVAILABLE = True
except ImportError:
    try:
        from pymodbus.server.sync import StartSerialServer, StartTcpServer
        from pymodbus.datastore import ModbusSequentialDataBlock, ModbusSlaveContext, ModbusServerContext
        MODBUS_AVAILABLE = True
    except ImportError:
        print("警告: pymodbus 模組不可用，Modbus 功能將被禁用")
        MODBUS_AVAILABLE = False
        StartSerialServer = None
        StartTcpServer = None
        ModbusSequentialDataBlock = None
        ModbusSlaveContext = None
        ModbusServerContext = None

import logging

class UARTReader:
    def __init__(self):
        self.config_manager = ConfigManager()
        self.serial_connection = None
        self.is_running = False
        self.latest_data = []
        self.max_data_count = None  # 無限制保存資料
        self.lock = threading.Lock()
        
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
        """清理超過30分鐘的舊數據"""
        try:
            from datetime import datetime, timedelta
            thirty_minutes_ago = datetime.now() - timedelta(minutes=30)
            
            # 計算清理前的數據量
            original_count = len(self.latest_data)
            
            # 過濾出30分鐘內的數據
            filtered_data = []
            for entry in self.latest_data:
                try:
                    # 解析時間戳
                    entry_timestamp = datetime.strptime(entry['timestamp'], '%Y-%m-%d %H:%M:%S')
                    if entry_timestamp >= thirty_minutes_ago:
                        filtered_data.append(entry)
                except ValueError:
                    # 如果時間戳解析失敗，保留該數據
                    filtered_data.append(entry)
            
            # 更新數據列表
            self.latest_data = filtered_data
            
            # 記錄清理結果
            cleaned_count = original_count - len(filtered_data)
            if cleaned_count > 0:
                logging.info(f"UART數據自動清理: 移除 {cleaned_count} 筆超過30分鐘的舊數據，剩餘 {len(filtered_data)} 筆")
                
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
    def start(self):
        if self.is_running:
            return
            
        if not MODBUS_AVAILABLE:
            logging.error("[TCP] 無法啟動TCP服務：pymodbus 模組不可用")
            return
            
        self.is_running = True
        # 強制重新載入配置，確保使用最新設定
        self.config_manager.load_config()
        config = self.config_manager.get_protocol_config('TCP')
        tcp_host = config.get('host', '0.0.0.0')
        tcp_port = config.get('port', 502)
        def run_server():
            try:
                StartTcpServer(self.context, address=(tcp_host, tcp_port))
                logging.info(f"[TCP] TCP伺服器啟動成功，host={tcp_host}, port={tcp_port}")
            except Exception as e:
                logging.exception(f"[TCP] Server啟動失敗: {e}")
        self.server_thread = threading.Thread(target=run_server, daemon=True)
        self.server_thread.start()
        logging.info(f"[TCP] 啟動TCP接收器，host={tcp_host}, port={tcp_port}")
    def stop(self):
        self.is_running = False
        logging.info("[TCP] 停止TCP接收器")
    def get_latest_data(self):
        return self.store.getValues(3, 0, 1000)
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
                StartSerialServer(self.context, port=com_port, baudrate=baud_rate, parity=parity, stopbits=stopbits, bytesize=bytesize, method='rtu')
                logging.info(f"[RTU] Server啟動成功，port={com_port}, baudrate={baud_rate}")
            except Exception as e:
                logging.exception(f"[RTU] Server啟動失敗: {e}")
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
    def start(self, protocol):
        # 停止其他協定
        for name, receiver in self.protocols.items():
            if hasattr(receiver, 'stop'):
                receiver.stop()
        # 啟動指定協定
        if protocol in self.protocols:
            self.protocols[protocol].start()
            self.active = protocol
            logging.info(f"[ProtocolManager] 啟用協定: {protocol}")
        else:
            logging.warning(f"[ProtocolManager] 不支援的協定: {protocol}")
    def get_latest_data(self):
        if self.active and self.active in self.protocols:
            return self.protocols[self.active].get_latest_data()
        return []

# 全域協定管理器實例
protocol_manager = ProtocolManager()

