"""
資料庫管理模組
處理 UART 資料的儲存和查詢功能
所有設備必須透過 db_setting.html 頁面手動註冊後才能儲存資料

修改說明：
- 移除自動設備發現功能
- 只有已註冊的設備才能儲存 UART 資料
- 設備必須透過 Web 介面手動註冊管理
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
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # 移除舊的 auto_created 欄位（如果存在）
                try:
                    cursor.execute('SELECT auto_created FROM device_info LIMIT 1')
                    # 如果欄位存在，創建新表並遷移資料
                    cursor.execute('''
                        CREATE TABLE IF NOT EXISTS device_info_new (
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
                    cursor.execute('''
                        INSERT INTO device_info_new 
                        (mac_id, device_name, device_type, device_model, factory_area, 
                         floor_level, location_description, installation_date, last_maintenance, 
                         status, created_at, updated_at)
                        SELECT mac_id, device_name, device_type, device_model, factory_area, 
                               floor_level, location_description, installation_date, last_maintenance, 
                               status, created_at, updated_at
                        FROM device_info
                    ''')
                    cursor.execute('DROP TABLE device_info')
                    cursor.execute('ALTER TABLE device_info_new RENAME TO device_info')
                    logging.info("已移除 auto_created 欄位")
                except sqlite3.OperationalError:
                    # 欄位不存在，忽略錯誤
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
        只有在設備已註冊的情況下才會儲存資料
        
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
                    
                    # 檢查設備是否已註冊
                    if not mac_id:
                        logging.warning("UART 資料中沒有 MAC ID，無法儲存")
                        return False
                    
                    # 檢查設備是否存在於 device_info 表中
                    cursor.execute('SELECT COUNT(*) FROM device_info WHERE mac_id = ?', (mac_id,))
                    device_exists = cursor.fetchone()[0] > 0
                    
                    if not device_exists:
                        logging.warning(f"設備 {mac_id} 尚未註冊，請先透過設定頁面註冊設備")
                        return False
                    
                    # 從 device_info 取得設備資訊
                    cursor.execute('''
                        SELECT device_type, device_model, factory_area, floor_level
                        FROM device_info WHERE mac_id = ?
                    ''', (mac_id,))
                    device_info_row = cursor.fetchone()
                    
                    if device_info_row:
                        device_type, device_model, factory_area, floor_level = device_info_row
                    else:
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
                        installation_date,
                        last_maintenance,
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

    # ====== 手動設備管理功能 ======
    # 所有設備必須透過 db_setting.html 頁面手動註冊
    
    # 以下自動設備發現功能已停用，設備必須手動註冊
    # def auto_discover_device(self, mac_id: str, uart_data: Optional[Dict] = None) -> Dict:
    # def _create_auto_device(self, mac_id: str, uart_data: Optional[Dict] = None) -> Dict:
    # def _infer_location_from_mac(self, mac_id: str, uart_data: Optional[Dict] = None) -> tuple:
    # def _generate_device_name(self, mac_id: str, factory_area: str, floor_level: str) -> str:
    # def _infer_device_model(self, mac_id: str, uart_data: Optional[Dict] = None) -> str:
    # def _get_fallback_device(self, mac_id: str) -> Dict:
    # def update_device_from_uart_data(self, mac_id: str, uart_data: Dict) -> bool:
    # def batch_discover_devices_from_history(self, limit: int = 1000) -> int:
    # def process_uart_data_with_auto_discovery(self, uart_data: Dict) -> bool:
    
    def check_device_registered(self, mac_id: str) -> bool:
        """
        檢查設備是否已註冊
        
        Args:
            mac_id: 設備 MAC ID
            
        Returns:
            bool: 設備是否已註冊
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT COUNT(*) FROM device_info WHERE mac_id = ?', (mac_id,))
                return cursor.fetchone()[0] > 0
        except sqlite3.Error as e:
            logging.error(f"檢查設備註冊狀態失敗: {e}")
            return False
    
    def get_unregistered_devices_from_uart_data(self, limit: int = 100) -> List[str]:
        """
        從 UART 資料中找出未註冊的設備 MAC ID
        
        Args:
            limit: 查詢限制
            
        Returns:
            List[str]: 未註冊的 MAC ID 列表
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 找出 uart_data 中存在但 device_info 中不存在的 MAC ID
                cursor.execute('''
                    SELECT DISTINCT u.mac_id
                    FROM uart_data u
                    LEFT JOIN device_info d ON u.mac_id = d.mac_id
                    WHERE u.mac_id IS NOT NULL 
                    AND u.mac_id != ''
                    AND d.mac_id IS NULL
                    ORDER BY u.timestamp DESC
                    LIMIT ?
                ''', (limit,))
                
                return [row[0] for row in cursor.fetchall()]
                
        except sqlite3.Error as e:
            logging.error(f"查詢未註冊設備失敗: {e}")
            return []
    
    def get_device_statistics(self) -> Dict:
        """取得設備管理統計資訊"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 總設備數
                cursor.execute('SELECT COUNT(*) FROM device_info')
                total_devices = cursor.fetchone()[0]
                
                # 活動設備數
                cursor.execute('SELECT COUNT(*) FROM device_info WHERE status = "active"')
                active_devices = cursor.fetchone()[0]
                
                # 非活動設備數
                inactive_devices = total_devices - active_devices
                
                # 有資料的設備數（最近24小時有資料的設備）
                last_24h = datetime.now() - timedelta(hours=24)
                cursor.execute('''
                    SELECT COUNT(DISTINCT u.mac_id) 
                    FROM uart_data u 
                    INNER JOIN device_info d ON u.mac_id = d.mac_id
                    WHERE u.timestamp >= ?
                ''', (last_24h.isoformat(),))
                devices_with_data = cursor.fetchone()[0]
                
                # 沒有資料的設備數
                devices_without_data = total_devices - devices_with_data
                
                return {
                    'total_devices_count': total_devices,
                    'active_devices_count': active_devices,
                    'inactive_devices_count': inactive_devices,
                    'devices_with_data_count': devices_with_data,
                    'devices_without_data_count': devices_without_data,
                    'last_update': datetime.now().isoformat()
                }
                
        except sqlite3.Error as e:
            logging.error(f"取得設備統計失敗: {e}")
            return {
                'total_devices_count': 0,
                'active_devices_count': 0,
                'inactive_devices_count': 0,
                'devices_with_data_count': 0,
                'devices_without_data_count': 0,
                'error': str(e),
                'last_update': datetime.now().isoformat()
            }

# 全域資料庫管理器實例
db_manager = DatabaseManager()
