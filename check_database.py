#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sqlite3
import json

def check_database():
    """檢查資料庫內容"""
    try:
        # 連接資料庫
        conn = sqlite3.connect('uart_data.db')
        cursor = conn.cursor()

        # 檢查資料表結構
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        print('資料表:', [table[0] for table in tables])

        # 檢查 device_info 表的內容
        print('\n=== device_info 表的內容 ===')
        cursor.execute('SELECT * FROM device_info')
        device_info_rows = cursor.fetchall()
        if device_info_rows:
            for row in device_info_rows:
                print(f'MAC: {row[0]}, 名稱: {row[1]}, 型號: {row[3]}, 廠區: {row[4]}, 樓層: {row[5]}')
        else:
            print('device_info 表為空')

        # 檢查 uart_data 表的數據量
        cursor.execute('SELECT COUNT(*) FROM uart_data')
        count = cursor.fetchone()[0]
        print(f'\nuart_data 表中有 {count} 筆數據')

        if count > 0:
            # 檢查廠區數據
            cursor.execute('SELECT DISTINCT factory_area FROM uart_data WHERE factory_area IS NOT NULL AND factory_area != ""')
            factory_areas = cursor.fetchall()
            print('廠區:', [area[0] for area in factory_areas])

            # 檢查樓層數據
            cursor.execute('SELECT DISTINCT floor_level FROM uart_data WHERE floor_level IS NOT NULL AND floor_level != ""')
            floor_levels = cursor.fetchall()
            print('樓層:', [floor[0] for floor in floor_levels])

            # 檢查 MAC ID 數據
            cursor.execute('SELECT DISTINCT mac_id FROM uart_data WHERE mac_id IS NOT NULL AND mac_id != ""')
            mac_ids = cursor.fetchall()
            print('MAC IDs:', [mac[0] for mac in mac_ids])

            # 檢查設備型號數據
            cursor.execute('SELECT DISTINCT device_model FROM uart_data WHERE device_model IS NOT NULL AND device_model != ""')
            device_models = cursor.fetchall()
            print('設備型號:', [model[0] for model in device_models])

            # 查看最新幾筆數據
            cursor.execute('SELECT timestamp, mac_id, factory_area, floor_level, device_model, current FROM uart_data ORDER BY timestamp DESC LIMIT 5')
            recent_data = cursor.fetchall()
            print('\n最新5筆數據:')
            for row in recent_data:
                print(f'  時間: {row[0]}, MAC: {row[1]}, 廠區: {row[2]}, 樓層: {row[3]}, 型號: {row[4]}, 電流: {row[5]}')
        else:
            print("資料庫為空，嘗試添加測試數據...")
            add_test_data(cursor)
            conn.commit()
            print("測試數據已添加")

        conn.close()
        
    except Exception as e:
        print(f"檢查資料庫時發生錯誤: {e}")

def add_test_data(cursor):
    """添加測試數據"""
    from datetime import datetime, timedelta
    import random
    
    base_time = datetime.now()
    
    # 測試數據
    test_data = [
        {
            'timestamp': (base_time - timedelta(minutes=i)).isoformat(),
            'mac_id': f'AA:BB:CC:DD:EE:{i:02d}',
            'device_type': 'H100',
            'device_model': 'H100-Pro' if i % 2 == 0 else 'H100-Lite',
            'factory_area': 'A廠區' if i % 3 == 0 else 'B廠區' if i % 3 == 1 else 'C廠區',
            'floor_level': f'{(i % 3) + 1}F',
            'temperature': round(20 + random.uniform(-5, 10), 2),
            'humidity': round(50 + random.uniform(-10, 20), 2),
            'voltage': round(220 + random.uniform(-10, 10), 2),
            'current': round(5 + random.uniform(-2, 3), 2),
            'power': None,
            'status': 'normal',
            'raw_data': json.dumps({'test': True}),
            'parsed_data': json.dumps({'test': True})
        }
        for i in range(10)
    ]
    
    for data in test_data:
        data['power'] = round(data['voltage'] * data['current'], 2) if data['voltage'] and data['current'] else None
        
        cursor.execute('''
            INSERT INTO uart_data (
                timestamp, mac_id, device_type, device_model,
                factory_area, floor_level, raw_data, parsed_data,
                temperature, humidity, voltage, current, power, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            data['timestamp'], data['mac_id'], data['device_type'], data['device_model'],
            data['factory_area'], data['floor_level'], data['raw_data'], data['parsed_data'],
            data['temperature'], data['humidity'], data['voltage'], data['current'], 
            data['power'], data['status']
        ))

if __name__ == '__main__':
    check_database()
