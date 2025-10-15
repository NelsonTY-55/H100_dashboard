"""
UART 服務
與 RAS_pi 系統同步的 UART 服務層
"""

import logging
import serial
import serial.tools.list_ports
import threading
import time
from typing import List, Dict, Optional, Callable

class UARTService:
    """UART 服務類 - 與 RAS_pi 系統同步"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.is_running = False
        self.serial_connection = None
        self.read_thread = None
        self.data_callback = None
        self.port = None
        self.baudrate = 9600
        self.data_buffer = []
        self.buffer_lock = threading.Lock()
        
    def list_available_ports(self) -> List[Dict]:
        """列出可用的串口"""
        try:
            ports = serial.tools.list_ports.comports()
            port_list = []
            
            for port in ports:
                port_info = {
                    'device': port.device,
                    'description': port.description,
                    'hwid': port.hwid,
                    'vid': port.vid,
                    'pid': port.pid,
                    'serial_number': port.serial_number,
                    'manufacturer': port.manufacturer
                }
                port_list.append(port_info)
                
            self.logger.info(f"找到 {len(port_list)} 個可用串口")
            return port_list
            
        except Exception as e:
            self.logger.error(f"列出串口失敗: {e}")
            return []
    
    def test_connection(self, port: str = None, baudrate: int = None) -> tuple:
        """測試串口連接"""
        test_port = port or self.port
        test_baudrate = baudrate or self.baudrate
        
        if not test_port:
            return False, "未指定串口"
        
        try:
            # 嘗試打開串口
            test_serial = serial.Serial(
                port=test_port,
                baudrate=test_baudrate,
                timeout=1
            )
            
            # 測試寫入和讀取
            test_serial.write(b'TEST\n')
            time.sleep(0.1)
            
            # 關閉測試連接
            test_serial.close()
            
            return True, f"串口 {test_port} 連接正常"
            
        except serial.SerialException as e:
            return False, f"串口連接失敗: {e}"
        except Exception as e:
            return False, f"測試失敗: {e}"
    
    def start_reading(self, port: str = None, baudrate: int = None) -> bool:
        """開始 UART 讀取"""
        if self.is_running:
            self.logger.warning("UART 服務已在運行")
            return True
        
        self.port = port or self.port
        self.baudrate = baudrate or self.baudrate
        
        if not self.port:
            self.logger.error("未指定串口")
            return False
        
        try:
            # 建立串口連接
            self.serial_connection = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=1
            )
            
            # 啟動讀取線程
            self.is_running = True
            self.read_thread = threading.Thread(target=self._read_loop)
            self.read_thread.daemon = True
            self.read_thread.start()
            
            self.logger.info(f"UART 服務已啟動 - 端口: {self.port}, 波特率: {self.baudrate}")
            return True
            
        except Exception as e:
            self.logger.error(f"啟動 UART 服務失敗: {e}")
            self.is_running = False
            return False
    
    def stop_reading(self) -> bool:
        """停止 UART 讀取"""
        if not self.is_running:
            self.logger.warning("UART 服務未運行")
            return True
        
        try:
            self.is_running = False
            
            # 等待讀取線程結束
            if self.read_thread and self.read_thread.is_alive():
                self.read_thread.join(timeout=2)
            
            # 關閉串口連接
            if self.serial_connection and self.serial_connection.is_open:
                self.serial_connection.close()
            
            self.logger.info("UART 服務已停止")
            return True
            
        except Exception as e:
            self.logger.error(f"停止 UART 服務失敗: {e}")
            return False
    
    def _read_loop(self):
        """UART 讀取循環"""
        while self.is_running and self.serial_connection and self.serial_connection.is_open:
            try:
                if self.serial_connection.in_waiting > 0:
                    data = self.serial_connection.readline().decode('utf-8', errors='ignore').strip()
                    
                    if data:
                        self._process_data(data)
                
                time.sleep(0.01)  # 避免 CPU 過載
                
            except Exception as e:
                self.logger.error(f"UART 讀取錯誤: {e}")
                if self.is_running:
                    time.sleep(1)  # 錯誤後等待重試
    
    def _process_data(self, data: str):
        """處理接收到的數據"""
        timestamp = time.time()
        
        # 將數據添加到緩衝區
        with self.buffer_lock:
            data_entry = {
                'timestamp': timestamp,
                'data': data,
                'raw': data
            }
            self.data_buffer.append(data_entry)
            
            # 限制緩衝區大小
            if len(self.data_buffer) > 1000:
                self.data_buffer = self.data_buffer[-500:]
        
        # 調用回調函數
        if self.data_callback:
            try:
                self.data_callback(data_entry)
            except Exception as e:
                self.logger.error(f"數據回調函數錯誤: {e}")
        
        self.logger.debug(f"收到數據: {data}")
    
    def send_data(self, data: str) -> bool:
        """發送數據"""
        if not self.is_running or not self.serial_connection:
            self.logger.error("UART 連接未建立")
            return False
        
        try:
            # 確保數據以換行符結尾
            if not data.endswith('\n'):
                data += '\n'
            
            self.serial_connection.write(data.encode('utf-8'))
            self.logger.debug(f"發送數據: {data.strip()}")
            return True
            
        except Exception as e:
            self.logger.error(f"發送數據失敗: {e}")
            return False
    
    def get_status(self) -> Dict:
        """獲取 UART 服務狀態"""
        status = {
            'is_running': self.is_running,
            'port': self.port,
            'baudrate': self.baudrate,
            'connected': self.serial_connection is not None and self.serial_connection.is_open if self.serial_connection else False,
            'data_count': len(self.data_buffer),
            'thread_alive': self.read_thread.is_alive() if self.read_thread else False
        }
        return status
    
    def get_data_buffer(self, limit: int = 100) -> List[Dict]:
        """獲取數據緩衝區內容"""
        with self.buffer_lock:
            return self.data_buffer[-limit:] if limit else self.data_buffer.copy()
    
    def clear_buffer(self):
        """清空數據緩衝區"""
        with self.buffer_lock:
            self.data_buffer.clear()
        self.logger.info("數據緩衝區已清空")
    
    def set_data_callback(self, callback: Callable):
        """設置數據回調函數"""
        self.data_callback = callback
        self.logger.info("數據回調函數已設置")

# 創建全局實例
uart_service = UARTService()