"""
資料庫管理模組
處理 UART 資料的儲存和查詢功能
"""

import sqlite3
import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import os
import threading

class DatabaseManager:
    def __init__(self, db_path: str = "uart_data.db"):
        """
        初始化資料庫管理器
        
        Args:
            db_path: 資料庫檔案路徑
        """
        self.db_path = db_path
        self.lock = threading.Lock()
        self._init_database()
        
    def _init_database(self):
        """初始化資料庫和表格"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 創建主要資料表
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS uart_data (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp DATETIME NOT NULL,
                        mac_id TEXT NOT NULL,
                        device_type TEXT,
                        device_model TEXT,
                        factory_area TEXT,
                        floor_level TEXT,
                        raw_data TEXT,
                        parsed_data TEXT,
                        temperature REAL,
                        humidity REAL,
                        voltage REAL,
                        current REAL,
                        power REAL,
                        status TEXT,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # 創建索引
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_uart_data_timestamp ON uart_data(timestamp)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_uart_data_mac_id ON uart_data(mac_id)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_uart_data_factory_area ON uart_data(factory_area)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_uart_data_floor_level ON uart_data(floor_level)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_uart_data_device_type ON uart_data(device_type)')
                
                # 創建設備資訊表
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS device_info (
                        mac_id TEXT PRIMARY KEY,
                        device_name TEXT,
                        device_type TEXT,
                        device_model TEXT,
                        factory_area TEXT,
                        floor_level TEXT,
                        location_description TEXT,
                        installation_date DATE,
                        last_maintenance DATE,
                        status TEXT DEFAULT 'active',
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # 創建廠區樓層資訊表
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS location_info (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        factory_area TEXT NOT NULL,
                        floor_level TEXT NOT NULL,
                        description TEXT,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(factory_area, floor_level)
                    )
                ''')
                
                conn.commit()
                logging.info("資料庫初始化完成")
                
        except sqlite3.Error as e:
            logging.error(f"資料庫初始化失敗: {e}")
            raise
    
    def save_uart_data(self, data: Dict) -> bool:
        """
        儲存 UART 資料到資料庫
        
        Args:
            data: UART 資料字典
            
        Returns:
            bool: 是否儲存成功
        """
        try:
            with self.lock:
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    
                    # 解析資料
                    timestamp = data.get('timestamp', datetime.now().isoformat())
                    mac_id = data.get('mac_id', data.get('MAC_ID', ''))
                    device_type = data.get('device_type', data.get('Device_Type', ''))
                    device_model = data.get('device_model', data.get('Device_Model', ''))
                    factory_area = data.get('factory_area', data.get('Factory_Area', ''))
                    floor_level = data.get('floor_level', data.get('Floor_Level', ''))
                    
                    # 提取感測器數據
                    temperature = self._extract_numeric_value(data, ['temperature', 'Temperature', 'temp'])
                    humidity = self._extract_numeric_value(data, ['humidity', 'Humidity', 'hum'])
                    voltage = self._extract_numeric_value(data, ['voltage', 'Voltage', 'V'])
                    current = self._extract_numeric_value(data, ['current', 'Current', 'I'])
                    power = self._extract_numeric_value(data, ['power', 'Power', 'P'])
                    
                    status = data.get('status', data.get('Status', 'normal'))
                    raw_data = json.dumps(data, ensure_ascii=False)
                    
                    # 解析後的資料
                    parsed_data = json.dumps({
                        'temperature': temperature,
                        'humidity': humidity,
                        'voltage': voltage,
                        'current': current,
                        'power': power,
                        'status': status
                    }, ensure_ascii=False)
                    
                    # 插入資料
                    cursor.execute('''
                        INSERT INTO uart_data (
                            timestamp, mac_id, device_type, device_model,
                            factory_area, floor_level, raw_data, parsed_data,
                            temperature, humidity, voltage, current, power, status
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        timestamp, mac_id, device_type, device_model,
                        factory_area, floor_level, raw_data, parsed_data,
                        temperature, humidity, voltage, current, power, status
                    ))
                    
                    conn.commit()
                    logging.debug(f"儲存 UART 資料成功: MAC={mac_id}")
                    return True
                    
        except Exception as e:
            logging.error(f"儲存 UART 資料失敗: {e}")
            return False
    
    def _extract_numeric_value(self, data: Dict, keys: List[str]) -> Optional[float]:
        """
        從資料中提取數值
        
        Args:
            data: 資料字典
            keys: 可能的鍵值列表
            
        Returns:
            float: 提取的數值，如果沒有找到則返回 None
        """
        for key in keys:
            if key in data:
                try:
                    value = data[key]
                    if isinstance(value, (int, float)):
                        return float(value)
                    elif isinstance(value, str):
                        # 嘗試從字串中提取數字
                        import re
                        numbers = re.findall(r'-?\d+\.?\d*', value)
                        if numbers:
                            return float(numbers[0])
                except (ValueError, TypeError):
                    continue
        return None
    
    def get_factory_areas(self) -> List[str]:
        """取得所有廠區列表"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT DISTINCT factory_area 
                    FROM uart_data 
                    WHERE factory_area IS NOT NULL AND factory_area != ''
                    ORDER BY factory_area
                ''')
                return [row[0] for row in cursor.fetchall()]
        except sqlite3.Error as e:
            logging.error(f"取得廠區列表失敗: {e}")
            return []
    
    def get_floor_levels(self, factory_area: str = None) -> List[str]:
        """取得樓層列表"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                if factory_area:
                    cursor.execute('''
                        SELECT DISTINCT floor_level 
                        FROM uart_data 
                        WHERE factory_area = ? AND floor_level IS NOT NULL AND floor_level != ''
                        ORDER BY floor_level
                    ''', (factory_area,))
                else:
                    cursor.execute('''
                        SELECT DISTINCT floor_level 
                        FROM uart_data 
                        WHERE floor_level IS NOT NULL AND floor_level != ''
                        ORDER BY floor_level
                    ''')
                return [row[0] for row in cursor.fetchall()]
        except sqlite3.Error as e:
            logging.error(f"取得樓層列表失敗: {e}")
            return []
    
    def get_mac_ids(self, factory_area: str = None, floor_level: str = None) -> List[str]:
        """取得 MAC ID 列表"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                sql = '''
                    SELECT DISTINCT mac_id 
                    FROM uart_data 
                    WHERE mac_id IS NOT NULL AND mac_id != ''
                '''
                params = []
                
                if factory_area:
                    sql += ' AND factory_area = ?'
                    params.append(factory_area)
                
                if floor_level:
                    sql += ' AND floor_level = ?'
                    params.append(floor_level)
                
                sql += ' ORDER BY mac_id'
                
                cursor.execute(sql, params)
                return [row[0] for row in cursor.fetchall()]
        except sqlite3.Error as e:
            logging.error(f"取得 MAC ID 列表失敗: {e}")
            return []
    
    def get_device_models(self, factory_area: str = None, floor_level: str = None, mac_id: str = None) -> List[str]:
        """取得設備型號列表"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                sql = '''
                    SELECT DISTINCT device_model 
                    FROM uart_data 
                    WHERE device_model IS NOT NULL AND device_model != ''
                '''
                params = []
                
                if factory_area:
                    sql += ' AND factory_area = ?'
                    params.append(factory_area)
                
                if floor_level:
                    sql += ' AND floor_level = ?'
                    params.append(floor_level)
                
                if mac_id:
                    sql += ' AND mac_id = ?'
                    params.append(mac_id)
                
                sql += ' ORDER BY device_model'
                
                cursor.execute(sql, params)
                return [row[0] for row in cursor.fetchall()]
        except sqlite3.Error as e:
            logging.error(f"取得設備型號列表失敗: {e}")
            return []
    
    def get_chart_data(self, 
                      factory_area: str = None, 
                      floor_level: str = None, 
                      mac_id: str = None, 
                      device_model: str = None,
                      start_time: datetime = None,
                      end_time: datetime = None,
                      data_type: str = 'temperature',
                      limit: int = 1000) -> List[Dict]:
        """
        取得圖表資料
        
        Args:
            factory_area: 廠區
            floor_level: 樓層
            mac_id: MAC ID
            device_model: 設備型號
            start_time: 開始時間
            end_time: 結束時間
            data_type: 資料類型 (temperature, humidity, voltage, current, power)
            limit: 資料筆數限制
            
        Returns:
            List[Dict]: 圖表資料
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 建構查詢條件
                sql = f'''
                    SELECT timestamp, {data_type}, mac_id, device_model, factory_area, floor_level
                    FROM uart_data
                    WHERE {data_type} IS NOT NULL
                '''
                params = []
                
                if factory_area:
                    sql += ' AND factory_area = ?'
                    params.append(factory_area)
                
                if floor_level:
                    sql += ' AND floor_level = ?'
                    params.append(floor_level)
                
                if mac_id:
                    sql += ' AND mac_id = ?'
                    params.append(mac_id)
                
                if device_model:
                    sql += ' AND device_model = ?'
                    params.append(device_model)
                
                if start_time:
                    sql += ' AND timestamp >= ?'
                    params.append(start_time.isoformat())
                
                if end_time:
                    sql += ' AND timestamp <= ?'
                    params.append(end_time.isoformat())
                
                sql += ' ORDER BY timestamp DESC'
                
                if limit:
                    sql += f' LIMIT {limit}'
                
                cursor.execute(sql, params)
                rows = cursor.fetchall()
                
                # 轉換為字典格式
                result = []
                for row in rows:
                    result.append({
                        'timestamp': row[0],
                        'value': row[1],
                        'mac_id': row[2],
                        'device_model': row[3],
                        'factory_area': row[4],
                        'floor_level': row[5]
                    })
                
                return result
                
        except sqlite3.Error as e:
            logging.error(f"取得圖表資料失敗: {e}")
            return []
    
    def get_latest_data(self, mac_id: str = None, limit: int = 10) -> List[Dict]:
        """取得最新資料"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                sql = '''
                    SELECT * FROM uart_data
                '''
                params = []
                
                if mac_id:
                    sql += ' WHERE mac_id = ?'
                    params.append(mac_id)
                
                sql += ' ORDER BY timestamp DESC'
                
                if limit:
                    sql += f' LIMIT {limit}'
                
                cursor.execute(sql, params)
                rows = cursor.fetchall()
                
                # 取得欄位名稱
                columns = [description[0] for description in cursor.description]
                
                # 轉換為字典格式
                result = []
                for row in rows:
                    result.append(dict(zip(columns, row)))
                
                return result
                
        except sqlite3.Error as e:
            logging.error(f"取得最新資料失敗: {e}")
            return []
    
    def register_device(self, device_info: Dict) -> bool:
        """註冊設備資訊"""
        try:
            with self.lock:
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    
                    cursor.execute('''
                        INSERT OR REPLACE INTO device_info (
                            mac_id, device_name, device_type, device_model,
                            factory_area, floor_level, location_description,
                            installation_date, last_maintenance, status, updated_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        device_info.get('mac_id'),
                        device_info.get('device_name'),
                        device_info.get('device_type'),
                        device_info.get('device_model'),
                        device_info.get('factory_area'),
                        device_info.get('floor_level'),
                        device_info.get('location_description'),
                        device_info.get('installation_date'),
                        device_info.get('last_maintenance'),
                        device_info.get('status', 'active'),
                        datetime.now().isoformat()
                    ))
                    
                    conn.commit()
                    logging.info(f"設備註冊成功: {device_info.get('mac_id')}")
                    return True
                    
        except sqlite3.Error as e:
            logging.error(f"設備註冊失敗: {e}")
            return False
    
    def get_device_info(self, mac_id: str = None) -> List[Dict]:
        """取得設備資訊"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                if mac_id:
                    cursor.execute('SELECT * FROM device_info WHERE mac_id = ?', (mac_id,))
                else:
                    cursor.execute('SELECT * FROM device_info ORDER BY mac_id')
                
                rows = cursor.fetchall()
                columns = [description[0] for description in cursor.description]
                
                result = []
                for row in rows:
                    result.append(dict(zip(columns, row)))
                
                return result
                
        except sqlite3.Error as e:
            logging.error(f"取得設備資訊失敗: {e}")
            return []
    
    def get_statistics(self) -> Dict:
        """取得統計資訊"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 總資料筆數
                cursor.execute('SELECT COUNT(*) FROM uart_data')
                total_records = cursor.fetchone()[0]
                
                # 設備數量
                cursor.execute('SELECT COUNT(DISTINCT mac_id) FROM uart_data WHERE mac_id IS NOT NULL')
                total_devices = cursor.fetchone()[0]
                
                # 廠區數量
                cursor.execute('SELECT COUNT(DISTINCT factory_area) FROM uart_data WHERE factory_area IS NOT NULL')
                total_areas = cursor.fetchone()[0]
                
                # 最新資料時間
                cursor.execute('SELECT MAX(timestamp) FROM uart_data')
                latest_timestamp = cursor.fetchone()[0]
                
                # 今日資料筆數
                today = datetime.now().date()
                cursor.execute('SELECT COUNT(*) FROM uart_data WHERE DATE(timestamp) = ?', (today,))
                today_records = cursor.fetchone()[0]
                
                return {
                    'total_records': total_records,
                    'total_devices': total_devices,
                    'total_areas': total_areas,
                    'latest_timestamp': latest_timestamp,
                    'today_records': today_records
                }
                
        except sqlite3.Error as e:
            logging.error(f"取得統計資訊失敗: {e}")
            return {}

# 全域資料庫管理器實例
db_manager = DatabaseManager()
