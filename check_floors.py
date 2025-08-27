#!/usr/bin/env python3
import sqlite3
import os

db_path = 'uart_data.db'
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 檢查 device_info 表中的樓層資料
    print('=== device_info 表中的樓層資料 ===')
    cursor.execute('SELECT DISTINCT factory_area, floor_level FROM device_info WHERE floor_level IS NOT NULL AND floor_level != ""')
    rows = cursor.fetchall()
    for row in rows:
        print(f'廠區: {row[0]}, 樓層: {row[1]}')
    
    # 檢查 uart_data 表中的樓層資料  
    print('\n=== uart_data 表中的樓層資料 ===')
    cursor.execute('SELECT DISTINCT factory_area, floor_level FROM uart_data WHERE floor_level IS NOT NULL AND floor_level != "" LIMIT 10')
    rows = cursor.fetchall()
    for row in rows:
        print(f'廠區: {row[0]}, 樓層: {row[1]}')
    
    # 測試 get_floor_levels 查詢
    print('\n=== 測試聯合查詢 ===')
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
    floors = [row[0] for row in cursor.fetchall()]
    print(f'所有樓層: {floors}')
    
    conn.close()
else:
    print('資料庫檔案不存在')
