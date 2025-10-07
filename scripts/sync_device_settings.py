#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import sqlite3
from datetime import datetime
import logging

def sync_device_settings_to_database():
    """將設備機台設定同步到資料庫"""
    try:
        # 讀取設備設定檔案
        with open('multi_device_settings.json', 'r', encoding='utf-8') as f:
            device_settings = json.load(f)
        
        # 連接資料庫
        conn = sqlite3.connect('uart_data.db')
        cursor = conn.cursor()
        
        print(f"找到 {len(device_settings)} 個設備設定")
        
        for mac_id, settings in device_settings.items():
            print(f"\n處理設備: {mac_id}")
            print(f"  設備名稱: {settings.get('device_name', 'N/A')}")
            print(f"  設備位置: {settings.get('device_location', 'N/A')}")
            
            # 準備設備資訊
            device_info = {
                'mac_id': mac_id,
                'device_name': settings.get('device_name', ''),
                'device_type': 'H100',  # 假設所有設備都是 H100 類型
                'device_model': settings.get('device_name', ''),  # 使用設備名稱作為型號
                'factory_area': parse_factory_area(settings.get('device_location', '')),
                'floor_level': parse_floor_level(settings.get('device_location', '')),
                'location_description': settings.get('device_location', ''),
                'installation_date': None,
                'last_maintenance': None,
                'status': 'active'
            }
            
            print(f"  將註冊到廠區: {device_info['factory_area']}")
            print(f"  將註冊到樓層: {device_info['floor_level']}")
            
            # 註冊設備到 device_info 表
            cursor.execute('''
                INSERT OR REPLACE INTO device_info (
                    mac_id, device_name, device_type, device_model,
                    factory_area, floor_level, location_description,
                    installation_date, last_maintenance, status,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            ''', (
                device_info['mac_id'],
                device_info['device_name'],
                device_info['device_type'],
                device_info['device_model'],
                device_info['factory_area'],
                device_info['floor_level'],
                device_info['location_description'],
                device_info['installation_date'],
                device_info['last_maintenance'],
                device_info['status']
            ))
            
            # 為該設備添加一些測試的 UART 數據
            add_sample_uart_data(cursor, mac_id, device_info)
        
        conn.commit()
        print(f"\n✅ 成功同步 {len(device_settings)} 個設備到資料庫")
        
        # 檢查同步結果
        print("\n=== 同步後的廠區列表 ===")
        cursor.execute('SELECT DISTINCT factory_area FROM device_info WHERE factory_area IS NOT NULL AND factory_area != ""')
        factory_areas = cursor.fetchall()
        print('廠區:', [area[0] for area in factory_areas])
        
        print("\n=== 同步後的樓層列表 ===")
        cursor.execute('SELECT DISTINCT floor_level FROM device_info WHERE floor_level IS NOT NULL AND floor_level != ""')
        floor_levels = cursor.fetchall()
        print('樓層:', [floor[0] for floor in floor_levels])
        
        print("\n=== uart_data 表中的廠區列表 ===")
        cursor.execute('SELECT DISTINCT factory_area FROM uart_data WHERE factory_area IS NOT NULL AND factory_area != ""')
        uart_factory_areas = cursor.fetchall()
        print('廠區:', [area[0] for area in uart_factory_areas])
        
        conn.close()
        
    except Exception as e:
        print(f"❌ 同步失敗: {e}")

def parse_factory_area(location):
    """從位置資訊解析廠區"""
    if not location:
        return '預設廠區'
    
    location = location.lower()
    if 'a' in location or '甲' in location:
        return 'A廠區'
    elif 'b' in location or '乙' in location:
        return 'B廠區'
    elif 'c' in location or '丙' in location:
        return 'C廠區'
    elif '測試' in location or 'test' in location:
        return '測試廠區'
    else:
        return location  # 直接使用原始位置資訊

def parse_floor_level(location):
    """從位置資訊解析樓層"""
    if not location:
        return '1F'
    
    import re
    # 尋找數字後跟 F 的模式
    match = re.search(r'(\d+)F?', location, re.IGNORECASE)
    if match:
        return f"{match.group(1)}F"
    
    # 如果沒有找到數字，根據關鍵字判斷
    location = location.lower()
    if '一樓' in location or '1樓' in location:
        return '1F'
    elif '二樓' in location or '2樓' in location:
        return '2F'
    elif '三樓' in location or '3樓' in location:
        return '3F'
    else:
        return '1F'  # 預設為 1 樓

def add_sample_uart_data(cursor, mac_id, device_info):
    """為設備添加一些範例 UART 數據"""
    from datetime import datetime, timedelta
    import random
    
    base_time = datetime.now()
    
    # 為每個設備添加最近 5 筆數據
    for i in range(5):
        timestamp = (base_time - timedelta(minutes=i*30)).isoformat()
        
        data = {
            'timestamp': timestamp,
            'mac_id': mac_id,
            'device_type': device_info['device_type'],
            'device_model': device_info['device_model'],
            'factory_area': device_info['factory_area'],
            'floor_level': device_info['floor_level'],
            'temperature': round(20 + random.uniform(-5, 10), 2),
            'humidity': round(50 + random.uniform(-10, 20), 2),
            'voltage': round(220 + random.uniform(-10, 10), 2),
            'current': round(5 + random.uniform(-2, 3), 2),
            'status': 'normal',
            'raw_data': json.dumps({'source': 'sync_script'}),
            'parsed_data': json.dumps({'source': 'sync_script'})
        }
        
        data['power'] = round(data['voltage'] * data['current'], 2)
        
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
    print("🔄 開始同步設備機台設定到資料庫...")
    sync_device_settings_to_database()
    print("✅ 同步完成！")
