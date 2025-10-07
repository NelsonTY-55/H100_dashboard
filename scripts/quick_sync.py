#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import sqlite3
from datetime import datetime
import random
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

        def parse_factory_area(location):
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
                return location

        def parse_floor_level(location):
            if not location:
                return '1F'
            
            match = re.search(r'(\d+)F?', location, re.IGNORECASE)
            if match:
                return f'{match.group(1)}F'
            return '1F'

        for mac_id, settings in device_settings.items():
            print(f'處理設備: {mac_id}')
            
            device_info = {
                'mac_id': mac_id,
                'device_name': settings.get('device_name', ''),
                'device_type': 'H100',
                'device_model': settings.get('device_name', ''),
                'factory_area': settings.get('device_name', ''),  # 廠區使用 device_name
                'floor_level': parse_floor_level(settings.get('device_location', '')),  # 樓層使用 device_location
                'location_description': settings.get('device_location', ''),
                'status': 'active'
            }
            
            print(f'  將註冊到廠區: {device_info["factory_area"]}')
            print(f'  將註冊到樓層: {device_info["floor_level"]}')
            
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
        cursor.execute('SELECT DISTINCT factory_area FROM device_info WHERE factory_area IS NOT NULL AND factory_area != ""')
        factory_areas = cursor.fetchall()
        print('廠區:', [area[0] for area in factory_areas])

        conn.close()
        return True
        
    except Exception as e:
        print(f'❌ 同步失敗: {e}')
        return False

if __name__ == '__main__':
    sync_devices()
