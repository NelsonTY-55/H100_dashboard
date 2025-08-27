"""
資料庫管理模組
處理 UART 資料的儲存和查詢功能
包含自動設備發現和管理功能
"""

import sqlite3
import json
import logging
import re
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
                        auto_created BOOLEAN DEFAULT 0,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # 檢查並添加 auto_created 欄位（向後相容）
                try:
                    cursor.execute('ALTER TABLE device_info ADD COLUMN auto_created BOOLEAN DEFAULT 0')
                except sqlite3.OperationalError:
                    # 欄位可能已存在，忽略錯誤
                    pass
                
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
        """取得所有廠區列表，優先從 device_info 表獲取最新資料"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                # 優先從 device_info 表獲取廠區，再從 uart_data 補充
                cursor.execute('''
                    SELECT DISTINCT factory_area 
                    FROM (
                        SELECT factory_area FROM device_info 
                        WHERE factory_area IS NOT NULL AND factory_area != ''
                        UNION
                        SELECT factory_area FROM uart_data 
                        WHERE factory_area IS NOT NULL AND factory_area != ''
                    ) AS combined
                    ORDER BY factory_area
                ''')
                return [row[0] for row in cursor.fetchall()]
        except sqlite3.Error as e:
            logging.error(f"取得廠區列表失敗: {e}")
            return []
    
    def get_floor_levels(self, factory_area: str = None) -> List[str]:
        """取得樓層列表，優先從 device_info 表獲取最新資料"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                if factory_area:
                    # 指定廠區時，先從 device_info 取得該廠區的樓層，再從 uart_data 補充
                    cursor.execute('''
                        SELECT DISTINCT floor_level 
                        FROM (
                            SELECT floor_level FROM device_info 
                            WHERE factory_area = ? AND floor_level IS NOT NULL AND floor_level != ''
                            UNION
                            SELECT floor_level FROM uart_data 
                            WHERE factory_area = ? AND floor_level IS NOT NULL AND floor_level != ''
                        ) AS combined
                        ORDER BY floor_level
                    ''', (factory_area, factory_area))
                else:
                    # 沒有指定廠區時，返回所有樓層（優先從 device_info 獲取）
                    cursor.execute('''
                        SELECT DISTINCT floor_level 
                        FROM (
                            SELECT floor_level FROM device_info 
                            WHERE floor_level IS NOT NULL AND floor_level != ''
                            UNION
                            SELECT floor_level FROM uart_data 
                            WHERE floor_level IS NOT NULL AND floor_level != ''
                        ) AS combined
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
                
                # 從兩個表中查詢 MAC ID
                if factory_area and floor_level:
                    sql = '''
                        SELECT DISTINCT mac_id 
                        FROM (
                            SELECT mac_id FROM uart_data 
                            WHERE mac_id IS NOT NULL AND mac_id != '' 
                            AND factory_area = ? AND floor_level = ?
                            UNION
                            SELECT mac_id FROM device_info 
                            WHERE mac_id IS NOT NULL AND mac_id != '' 
                            AND factory_area = ? AND floor_level = ?
                        ) AS combined
                        ORDER BY mac_id
                    '''
                    params = [factory_area, floor_level, factory_area, floor_level]
                elif factory_area:
                    sql = '''
                        SELECT DISTINCT mac_id 
                        FROM (
                            SELECT mac_id FROM uart_data 
                            WHERE mac_id IS NOT NULL AND mac_id != '' 
                            AND factory_area = ?
                            UNION
                            SELECT mac_id FROM device_info 
                            WHERE mac_id IS NOT NULL AND mac_id != '' 
                            AND factory_area = ?
                        ) AS combined
                        ORDER BY mac_id
                    '''
                    params = [factory_area, factory_area]
                elif floor_level:
                    sql = '''
                        SELECT DISTINCT mac_id 
                        FROM (
                            SELECT mac_id FROM uart_data 
                            WHERE mac_id IS NOT NULL AND mac_id != '' 
                            AND floor_level = ?
                            UNION
                            SELECT mac_id FROM device_info 
                            WHERE mac_id IS NOT NULL AND mac_id != '' 
                            AND floor_level = ?
                        ) AS combined
                        ORDER BY mac_id
                    '''
                    params = [floor_level, floor_level]
                else:
                    sql = '''
                        SELECT DISTINCT mac_id 
                        FROM (
                            SELECT mac_id FROM uart_data 
                            WHERE mac_id IS NOT NULL AND mac_id != ''
                            UNION
                            SELECT mac_id FROM device_info 
                            WHERE mac_id IS NOT NULL AND mac_id != ''
                        ) AS combined
                        ORDER BY mac_id
                    '''
                    params = []
                
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
                
                # 從兩個表中查詢設備型號
                conditions = []
                params = []
                
                if factory_area:
                    conditions.append('factory_area = ?')
                    params.append(factory_area)
                
                if floor_level:
                    conditions.append('floor_level = ?')
                    params.append(floor_level)
                
                if mac_id:
                    conditions.append('mac_id = ?')
                    params.append(mac_id)
                
                where_clause = ''
                if conditions:
                    where_clause = ' AND ' + ' AND '.join(conditions)
                
                sql = f'''
                    SELECT DISTINCT device_model 
                    FROM (
                        SELECT device_model FROM uart_data 
                        WHERE device_model IS NOT NULL AND device_model != ''{where_clause}
                        UNION
                        SELECT device_model FROM device_info 
                        WHERE device_model IS NOT NULL AND device_model != ''{where_clause}
                    ) AS combined
                    ORDER BY device_model
                '''
                
                # 每個條件需要重複參數，因為有兩個查詢
                all_params = params + params
                
                cursor.execute(sql, all_params)
                return [row[0] for row in cursor.fetchall()]
        except sqlite3.Error as e:
            logging.error(f"取得設備型號列表失敗: {e}")
            return []
    
    def get_chart_data(self, data_type: str = 'current', filters: Dict = None, limit: int = 1000) -> List[Dict]:
        """
        取得圖表資料
        
        Args:
            data_type: 資料類型 (temperature, humidity, voltage, current, power)
            filters: 篩選條件字典
            limit: 資料筆數限制
            
        Returns:
            List[Dict]: 圖表資料，格式為 [{'x': timestamp, 'y': value}, ...]
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 建構查詢條件
                sql = f'''
                    SELECT timestamp, {data_type}
                    FROM uart_data
                    WHERE {data_type} IS NOT NULL
                '''
                params = []
                
                if filters:
                    if 'factory_area' in filters:
                        sql += ' AND factory_area = ?'
                        params.append(filters['factory_area'])
                    
                    if 'floor_level' in filters:
                        sql += ' AND floor_level = ?'
                        params.append(filters['floor_level'])
                    
                    if 'mac_id' in filters:
                        sql += ' AND mac_id = ?'
                        params.append(filters['mac_id'])
                    
                    if 'device_model' in filters:
                        sql += ' AND device_model = ?'
                        params.append(filters['device_model'])
                
                sql += ' ORDER BY timestamp ASC'
                
                if limit:
                    sql += f' LIMIT {limit}'
                
                cursor.execute(sql, params)
                rows = cursor.fetchall()
                
                # 轉換為圖表格式
                result = []
                for row in rows:
                    result.append({
                        'x': row[0],
                        'y': row[1]
                    })
                
                return result
                
        except sqlite3.Error as e:
            logging.error(f"取得圖表資料失敗: {e}")
            return []
    
    def get_latest_data(self, filters: Dict = None, limit: int = 10) -> List[Dict]:
        """取得最新資料"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                sql = '''
                    SELECT timestamp, mac_id, device_model, factory_area, floor_level,
                           temperature, humidity, voltage, current, power, status
                    FROM uart_data
                    WHERE 1=1
                '''
                params = []
                
                if filters:
                    if 'factory_area' in filters:
                        sql += ' AND factory_area = ?'
                        params.append(filters['factory_area'])
                    
                    if 'floor_level' in filters:
                        sql += ' AND floor_level = ?'
                        params.append(filters['floor_level'])
                    
                    if 'mac_id' in filters:
                        sql += ' AND mac_id = ?'
                        params.append(filters['mac_id'])
                    
                    if 'device_model' in filters:
                        sql += ' AND device_model = ?'
                        params.append(filters['device_model'])
                
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
                        'mac_id': row[1],
                        'device_model': row[2],
                        'factory_area': row[3],
                        'floor_level': row[4],
                        'temperature': row[5],
                        'humidity': row[6],
                        'voltage': row[7],
                        'current': row[8],
                        'power': row[9],
                        'status': row[10]
                    })
                
                return result
                
        except sqlite3.Error as e:
            logging.error(f"取得最新資料失敗: {e}")
            return []
    
    def get_statistics(self, filters: Dict = None) -> Dict:
        """取得統計資訊"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 建構基本查詢條件
                where_clause = "WHERE 1=1"
                params = []
                
                if filters:
                    if 'factory_area' in filters:
                        where_clause += ' AND factory_area = ?'
                        params.append(filters['factory_area'])
                    
                    if 'floor_level' in filters:
                        where_clause += ' AND floor_level = ?'
                        params.append(filters['floor_level'])
                    
                    if 'mac_id' in filters:
                        where_clause += ' AND mac_id = ?'
                        params.append(filters['mac_id'])
                    
                    if 'device_model' in filters:
                        where_clause += ' AND device_model = ?'
                        params.append(filters['device_model'])
                
                # 總資料筆數
                cursor.execute(f'SELECT COUNT(*) FROM uart_data {where_clause}', params)
                total_records = cursor.fetchone()[0]
                
                # 電流統計
                cursor.execute(f'SELECT AVG(current), MAX(current), MIN(current) FROM uart_data {where_clause} AND current IS NOT NULL', params)
                current_stats = cursor.fetchone()
                
                # 溫度統計
                cursor.execute(f'SELECT AVG(temperature), MAX(temperature), MIN(temperature) FROM uart_data {where_clause} AND temperature IS NOT NULL', params)
                temp_stats = cursor.fetchone()
                
                # 電壓統計
                cursor.execute(f'SELECT AVG(voltage), MAX(voltage), MIN(voltage) FROM uart_data {where_clause} AND voltage IS NOT NULL', params)
                voltage_stats = cursor.fetchone()
                
                # 最新資料時間
                cursor.execute(f'SELECT MAX(timestamp) FROM uart_data {where_clause}', params)
                latest_timestamp = cursor.fetchone()[0]
                
                # 今日資料筆數
                today = datetime.now().date()
                cursor.execute(f'SELECT COUNT(*) FROM uart_data {where_clause} AND DATE(timestamp) = ?', params + [today])
                today_records = cursor.fetchone()[0]
                
                return {
                    'total_records': total_records,
                    'avg_current': current_stats[0] if current_stats[0] else 0,
                    'max_current': current_stats[1] if current_stats[1] else 0,
                    'min_current': current_stats[2] if current_stats[2] else 0,
                    'avg_temperature': temp_stats[0] if temp_stats[0] else 0,
                    'max_temperature': temp_stats[1] if temp_stats[1] else 0,
                    'min_temperature': temp_stats[2] if temp_stats[2] else 0,
                    'avg_voltage': voltage_stats[0] if voltage_stats[0] else 0,
                    'max_voltage': voltage_stats[1] if voltage_stats[1] else 0,
                    'min_voltage': voltage_stats[2] if voltage_stats[2] else 0,
                    'latest_timestamp': latest_timestamp,
                    'today_records': today_records
                }
                
        except sqlite3.Error as e:
            logging.error(f"取得統計資訊失敗: {e}")
            return {}
    
    def register_device(self, device_info: Dict) -> bool:
        """註冊設備資訊"""
        try:
            with self.lock:
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    
                    # 確保日期欄位是字串或 None
                    installation_date = device_info.get('installation_date')
                    last_maintenance = device_info.get('last_maintenance')
                    
                    # 如果是 datetime 物件，轉換為 ISO 格式字串
                    if hasattr(installation_date, 'isoformat'):
                        installation_date = installation_date.isoformat()
                    elif installation_date is not None and not isinstance(installation_date, str):
                        installation_date = str(installation_date)
                    
                    if hasattr(last_maintenance, 'isoformat'):
                        last_maintenance = last_maintenance.isoformat()
                    elif last_maintenance is not None and not isinstance(last_maintenance, str):
                        last_maintenance = str(last_maintenance)
                    
                    cursor.execute('''
                        INSERT OR REPLACE INTO device_info (
                            mac_id, device_name, device_type, device_model,
                            factory_area, floor_level, location_description,
                            installation_date, last_maintenance, status, auto_created, updated_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        device_info.get('mac_id'),
                        device_info.get('device_name'),
                        device_info.get('device_type'),
                        device_info.get('device_model'),
                        device_info.get('factory_area'),
                        device_info.get('floor_level'),
                        device_info.get('location_description'),
                        installation_date,
                        last_maintenance,
                        device_info.get('status', 'active'),
                        device_info.get('auto_created', False),
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
    
    def delete_device(self, mac_id: str) -> bool:
        """刪除設備資訊"""
        try:
            with self.lock:
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    
                    # 檢查設備是否存在
                    cursor.execute('SELECT COUNT(*) FROM device_info WHERE mac_id = ?', (mac_id,))
                    count = cursor.fetchone()[0]
                    
                    if count == 0:
                        logging.warning(f"設備 {mac_id} 不存在")
                        return False
                    
                    # 刪除設備資訊
                    cursor.execute('DELETE FROM device_info WHERE mac_id = ?', (mac_id,))
                    conn.commit()
                    
                    logging.info(f"設備 {mac_id} 已刪除")
                    return True
                    
        except sqlite3.Error as e:
            logging.error(f"刪除設備失敗: {e}")
            return False

    def get_current_data(self, filters: Dict) -> List[Dict]:
        """
        獲取電流數據
        
        Args:
            filters: 篩選條件字典，包含：
                - factory_area: 廠區
                - floor_level: 樓層
                - mac_id: MAC ID
                - device_model: 設備型號
                - time_range: 時間範圍（分鐘）
        
        Returns:
            List[Dict]: 電流數據列表
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 構建查詢條件
                where_conditions = []
                params = []
                
                if filters.get('factory_area'):
                    where_conditions.append('factory_area = ?')
                    params.append(filters['factory_area'])
                
                if filters.get('floor_level'):
                    where_conditions.append('floor_level = ?')
                    params.append(filters['floor_level'])
                
                if filters.get('mac_id'):
                    where_conditions.append('mac_id = ?')
                    params.append(filters['mac_id'])
                
                if filters.get('device_model'):
                    where_conditions.append('device_model = ?')
                    params.append(filters['device_model'])
                
                # 時間範圍條件
                time_range = filters.get('time_range', 10)  # 預設10分鐘
                time_limit = datetime.now() - timedelta(minutes=int(time_range))
                where_conditions.append('timestamp >= ?')
                params.append(time_limit.isoformat())
                
                # 只查詢有電流數據的記錄
                where_conditions.append('current IS NOT NULL')
                
                where_clause = 'WHERE ' + ' AND '.join(where_conditions) if where_conditions else ''
                
                query = f'''
                    SELECT timestamp, mac_id, device_model, factory_area, floor_level, current, 'A' as unit, 0 as channel
                    FROM uart_data
                    {where_clause}
                    ORDER BY timestamp DESC
                    LIMIT 1000
                '''
                
                cursor.execute(query, params)
                rows = cursor.fetchall()
                
                # 轉換為字典格式
                columns = ['timestamp', 'mac_id', 'device_model', 'factory_area', 'floor_level', 'value', 'unit', 'channel']
                current_data = []
                for row in rows:
                    data_dict = dict(zip(columns, row))
                    current_data.append(data_dict)
                
                logging.info(f"查詢到 {len(current_data)} 筆電流數據")
                return current_data
                
        except sqlite3.Error as e:
            logging.error(f"查詢電流數據失敗: {e}")
            return []

    # ====== 自動設備管理功能 ======
    
    def auto_discover_device(self, mac_id: str, uart_data: Optional[Dict] = None) -> Dict:
        """
        自動發現並建立設備資訊
        
        Args:
            mac_id: 設備 MAC ID
            uart_data: 可選的 UART 資料，用於推斷設備資訊
            
        Returns:
            Dict: 設備資訊
        """
        try:
            # 檢查設備是否已存在
            existing_device = self.get_device_info(mac_id)
            if existing_device and len(existing_device) > 0:
                logging.info(f"設備 {mac_id} 已存在於資料庫")
                return existing_device[0]
            
            # 自動建立新設備
            device_info = self._create_auto_device(mac_id, uart_data)
            
            # 儲存到資料庫
            if self.register_device(device_info):
                logging.info(f"自動建立設備 {mac_id} 成功")
                return device_info
            else:
                logging.error(f"自動建立設備 {mac_id} 失敗")
                return self._get_fallback_device(mac_id)
                
        except Exception as e:
            logging.error(f"自動發現設備 {mac_id} 時發生錯誤: {e}")
            return self._get_fallback_device(mac_id)
    
    def _create_auto_device(self, mac_id: str, uart_data: Optional[Dict] = None) -> Dict:
        """自動建立設備資訊"""
        current_time = datetime.now().isoformat()
        
        # 解析廠區和樓層（從 MAC ID 或 UART 資料推斷）
        factory_area, floor_level = self._infer_location_from_mac(mac_id, uart_data)
        
        # 推斷設備名稱
        device_name = self._generate_device_name(mac_id, factory_area, floor_level)
        
        device_info = {
            'mac_id': mac_id,
            'device_name': device_name,
            'device_type': 'H100',
            'device_model': self._infer_device_model(mac_id, uart_data),
            'factory_area': factory_area,
            'floor_level': floor_level,
            'location_description': f"{factory_area}-{floor_level} (自動分配)",
            'installation_date': current_time,
            'last_maintenance': None,
            'status': 'active',
            'auto_created': True,  # 標記為自動建立
            'created_at': current_time,
            'updated_at': current_time
        }
        
        return device_info
    
    def _infer_location_from_mac(self, mac_id: str, uart_data: Optional[Dict] = None) -> tuple:
        """從 MAC ID 和 UART 資料推斷位置資訊"""
        
        # 方法 1: 從 UART 資料中取得位置資訊
        if uart_data:
            factory_area = None
            floor_level = None
            
            # 檢查各種可能的廠區欄位名稱
            for key in ['factory_area', 'Factory_Area', 'factoryArea', 'area']:
                if key in uart_data and uart_data[key]:
                    factory_area = uart_data[key]
                    break
            
            # 檢查各種可能的樓層欄位名稱
            for key in ['floor_level', 'Floor_Level', 'floorLevel', 'floor']:
                if key in uart_data and uart_data[key]:
                    floor_level = uart_data[key]
                    break
                    
            if factory_area and floor_level:
                return factory_area, floor_level
        
        # 方法 2: 從 MAC ID 模式推斷
        try:
            mac_parts = mac_id.replace(':', '').replace('-', '').upper()
            if len(mac_parts) >= 6:
                # 使用最後兩個字元來決定廠區
                area_code = int(mac_parts[-2], 16) % 3  # 0, 1, 2
                area_map = {0: 'A廠區', 1: 'B廠區', 2: 'C廠區'}
                factory_area = area_map.get(area_code, 'A廠區')
                
                # 使用最後一個字元來決定樓層
                floor_code = int(mac_parts[-1], 16) % 5 + 1  # 1-5
                floor_level = f"{floor_code}F"
                
                return factory_area, floor_level
        except Exception:
            pass
        
        # 方法 3: 預設值
        return '自動分配廠區', '1F'
    
    def _generate_device_name(self, mac_id: str, factory_area: str, floor_level: str) -> str:
        """生成設備名稱"""
        # 取 MAC ID 的最後 4 個字元作為設備識別
        mac_suffix = mac_id.replace(':', '').replace('-', '')[-4:].upper()
        return f"{factory_area}-{floor_level}-{mac_suffix}"
    
    def _infer_device_model(self, mac_id: str, uart_data: Optional[Dict] = None) -> str:
        """推斷設備型號"""
        # 從 UART 資料推斷
        if uart_data:
            model_keys = ['device_model', 'Device_Model', 'model', 'Model', 'deviceModel']
            for key in model_keys:
                if key in uart_data and uart_data[key]:
                    return uart_data[key]
        
        # 從 MAC ID 推斷
        try:
            mac_parts = mac_id.replace(':', '').replace('-', '').upper()
            if len(mac_parts) >= 4:
                # 使用前兩個字元來推斷型號
                model_code = mac_parts[:2]
                model_map = {
                    'AA': 'H100-Standard',
                    'BB': 'H100-Pro',
                    'CC': 'H100-Lite'
                }
                return model_map.get(model_code, 'H100-Unknown')
        except Exception:
            pass
        
        return 'H100-Auto'
    
    def _get_fallback_device(self, mac_id: str) -> Dict:
        """取得備用設備資訊（當自動建立失敗時使用）"""
        current_time = datetime.now().isoformat()
        return {
            'mac_id': mac_id,
            'device_name': f"未知設備-{mac_id[-4:]}",
            'device_type': 'H100',
            'device_model': 'H100-Unknown',
            'factory_area': '未分配廠區',
            'floor_level': '1F',
            'location_description': '位置待確認',
            'installation_date': current_time,
            'last_maintenance': None,
            'status': 'unknown',
            'auto_created': True,
            'created_at': current_time,
            'updated_at': current_time
        }
    
    def update_device_from_uart_data(self, mac_id: str, uart_data: Dict) -> bool:
        """根據 UART 資料更新設備資訊"""
        try:
            # 取得現有設備資訊
            existing_device_list = self.get_device_info(mac_id)
            
            if not existing_device_list or len(existing_device_list) == 0:
                # 如果設備不存在，自動建立
                self.auto_discover_device(mac_id, uart_data)
                return True
            
            existing_device = existing_device_list[0]
            
            # 更新設備資訊
            updated = False
            update_data = existing_device.copy()
            
            # 檢查是否需要更新廠區和樓層
            if 'factory_area' in uart_data and uart_data['factory_area']:
                if update_data.get('factory_area') != uart_data['factory_area']:
                    update_data['factory_area'] = uart_data['factory_area']
                    updated = True
            
            if 'floor_level' in uart_data and uart_data['floor_level']:
                if update_data.get('floor_level') != uart_data['floor_level']:
                    update_data['floor_level'] = uart_data['floor_level']
                    updated = True
            
            # 檢查是否需要更新設備型號
            if 'device_model' in uart_data and uart_data['device_model']:
                if update_data.get('device_model') != uart_data['device_model']:
                    update_data['device_model'] = uart_data['device_model']
                    updated = True
            
            if updated:
                update_data['updated_at'] = datetime.now().isoformat()
                return self.register_device(update_data)
            
            return True  # 沒有變更也算成功
            
        except Exception as e:
            logging.error(f"更新設備 {mac_id} 失敗: {e}")
            return False
    
    def get_auto_device_statistics(self) -> Dict:
        """取得自動設備管理統計資訊"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 總設備數
                cursor.execute('SELECT COUNT(*) FROM device_info')
                total_devices = cursor.fetchone()[0]
                
                # 自動建立的設備數
                cursor.execute('SELECT COUNT(*) FROM device_info WHERE auto_created = 1')
                auto_devices = cursor.fetchone()[0]
                
                # 手動建立的設備數
                manual_devices = total_devices - auto_devices
                
                # 活動設備數
                cursor.execute('SELECT COUNT(*) FROM device_info WHERE status = "active"')
                active_devices = cursor.fetchone()[0]
                
                # 非活動設備數
                inactive_devices = total_devices - active_devices
                
                return {
                    'total_devices_count': total_devices,
                    'auto_devices_count': auto_devices,
                    'manual_devices_count': manual_devices,
                    'active_devices_count': active_devices,
                    'inactive_devices_count': inactive_devices,
                    'last_update': datetime.now().isoformat()
                }
                
        except sqlite3.Error as e:
            logging.error(f"取得自動設備統計失敗: {e}")
            return {
                'total_devices_count': 0,
                'auto_devices_count': 0,
                'manual_devices_count': 0,
                'active_devices_count': 0,
                'inactive_devices_count': 0,
                'error': str(e),
                'last_update': datetime.now().isoformat()
            }
    
    def batch_discover_devices_from_history(self, limit: int = 1000) -> int:
        """從歷史 UART 資料批次發現設備"""
        try:
            # 取得所有 UART 資料中的唯一 MAC ID
            discovered_count = 0
            processed_macs = set()
            
            # 取得最近的 UART 資料
            recent_data = self.get_latest_data(filters={}, limit=limit)
            
            for data_entry in recent_data:
                mac_id = data_entry.get('mac_id')
                if mac_id and mac_id not in processed_macs:
                    processed_macs.add(mac_id)
                    
                    # 準備 UART 資料格式
                    uart_data = {
                        'mac_id': mac_id,
                        'factory_area': data_entry.get('factory_area'),
                        'floor_level': data_entry.get('floor_level'),
                        'device_model': data_entry.get('device_model'),
                        'device_type': data_entry.get('device_type', 'H100'),
                        'timestamp': data_entry.get('timestamp')
                    }
                    
                    # 嘗試發現設備
                    device_info = self.auto_discover_device(mac_id, uart_data)
                    if device_info:
                        discovered_count += 1
                        logging.info(f"批次發現設備: {mac_id} -> {device_info.get('device_name', 'N/A')}")
            
            logging.info(f"批次發現完成，共處理 {len(processed_macs)} 個 MAC ID，成功發現 {discovered_count} 個設備")
            return discovered_count
            
        except Exception as e:
            logging.error(f"批次發現設備時發生錯誤: {e}")
            return 0
    
    def process_uart_data_with_auto_discovery(self, uart_data: Dict) -> bool:
        """
        處理 UART 資料並自動發現設備
        
        Args:
            uart_data: UART 資料字典
            
        Returns:
            bool: 處理是否成功
        """
        try:
            # 提取 MAC ID
            mac_id = uart_data.get('mac_id') or uart_data.get('MAC_ID') or uart_data.get('Mac_ID')
            
            if not mac_id:
                logging.warning("UART 資料中沒有 MAC ID，無法自動發現設備")
                return False
            
            # 使用自動設備管理器更新設備資訊
            success = self.update_device_from_uart_data(mac_id, uart_data)
            
            if success:
                logging.debug(f"設備 {mac_id} 資訊已通過 UART 資料自動更新")
            
            # 儲存 UART 資料到資料庫
            db_success = self.save_uart_data(uart_data)
            if db_success:
                logging.debug(f"UART 資料已儲存，MAC ID: {mac_id}")
            
            return success and db_success
            
        except Exception as e:
            logging.error(f"處理 UART 資料自動發現時發生錯誤: {e}")
            return False

# 全域資料庫管理器實例
db_manager = DatabaseManager()
