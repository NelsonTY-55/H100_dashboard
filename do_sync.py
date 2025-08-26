#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import sqlite3
from datetime import datetime
import re

def sync_devices():
    """同步設備設定到資料庫"""
    try:
        # 讀取設備設定檔案
        with open('multi_device_settings.json', 'r', encoding='utf-8') as f:
            device_settings = json.load(f)

        # 連接資料庫
        conn = sqlite3.connect('uart_data.db')
        cursor = conn.cursor()

        print(f'找到 {len(device_settings)} 個設備設定')

        def parse_floor_level(location):
            if not location:
                return '1F'
            
            match = re.search(r'(\d+)F?', location, re.IGNORECASE)
            if match:
                return f'{match.group(1)}F'
            return '1F'

        for mac_id, settings in device_settings.items():
            print(f'處理設備: {mac_id}')
            
            # 廠區使用 device_name，樓層使用 device_location
            device_info = {
                'mac_id': mac_id,
                'device_name': settings.get('device_name', ''),
                'device_type': 'H100',
                'device_model': settings.get('device_name', ''),
                'factory_area': settings.get('device_name', ''),  # 廠區 = device_name
                'floor_level': parse_floor_level(settings.get('device_location', '')),  # 樓層從 device_location 解析
                'location_description': settings.get('device_location', ''),
                'status': 'active'
            }
            
            print(f'  廠區: {device_info["factory_area"]}')
            print(f'  樓層: {device_info["floor_level"]}')
            
            cursor.execute('''
                INSERT OR REPLACE INTO device_info (
                    mac_id, device_name, device_type, device_model,
                    factory_area, floor_level, location_description,
                    status, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            ''', (
                device_info['mac_id'],
                device_info['device_name'],
                device_info['device_type'],
                device_info['device_model'],
                device_info['factory_area'],
                device_info['floor_level'],
                device_info['location_description'],
                device_info['status']
            ))

        conn.commit()
        print(f'✅ 成功同步 {len(device_settings)} 個設備到資料庫')

        # 檢查同步結果
        print('\n=== 同步後的廠區列表 ===')
        cursor.execute('SELECT DISTINCT factory_area FROM device_info WHERE factory_area IS NOT NULL AND factory_area != ""')
        areas = [row[0] for row in cursor.fetchall()]
        print('device_info 表中的廠區:', areas)

        print('\n=== 同步後的樓層列表 ===')
        cursor.execute('SELECT DISTINCT floor_level FROM device_info WHERE floor_level IS NOT NULL AND floor_level != ""')
        floors = [row[0] for row in cursor.fetchall()]
        print('device_info 表中的樓層:', floors)

        print('\n=== 設備詳細資訊 ===')
        cursor.execute('SELECT mac_id, device_name, factory_area, floor_level FROM device_info')
        devices = cursor.fetchall()
        for device in devices:
            print(f'MAC: {device[0]}, 名稱: {device[1]}, 廠區: {device[2]}, 樓層: {device[3]}')

        conn.close()
        return True
        
    except Exception as e:
        print(f'❌ 同步失敗: {e}')
        return False

if __name__ == '__main__':
    sync_devices()
