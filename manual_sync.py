#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sqlite3
import json
from datetime import datetime

def add_test_device_with_location():
    """添加一個帶有廠區和樓層資訊的測試設備"""
    try:
        # 連接資料庫
        conn = sqlite3.connect('uart_data.db')
        cursor = conn.cursor()
        
        # 讀取現有的設備設定
        with open('multi_device_settings.json', 'r', encoding='utf-8') as f:
            device_settings = json.load(f)
        
        print(f"處理 {len(device_settings)} 個設備設定...")
        
        for mac_id, settings in device_settings.items():
            device_name = settings.get('device_name', '')
            device_location = settings.get('device_location', '')
            
            # 解析廠區和樓層
            if '1F' in device_location or '一樓' in device_location:
                factory_area = 'A廠區'
                floor_level = '1F'
            elif 'ATC' in device_name:
                factory_area = 'B廠區' 
                floor_level = '2F'
            else:
                factory_area = 'C廠區'
                floor_level = '3F'
            
            # 添加設備資訊到 device_info 表
            cursor.execute('''
                INSERT OR REPLACE INTO device_info (
                    mac_id, device_name, device_type, device_model,
                    factory_area, floor_level, location_description,
                    installation_date, last_maintenance, status,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            ''', (
                mac_id,
                device_name,
                'H100',
                device_name,
                factory_area,
                floor_level,
                device_location,
                None,
                None,
                'active'
            ))
            
            # 添加一些 UART 數據到 uart_data 表
            for i in range(3):
                timestamp = datetime.now().isoformat()
                
                cursor.execute('''
                    INSERT INTO uart_data (
                        timestamp, mac_id, device_type, device_model,
                        factory_area, floor_level, raw_data, parsed_data,
                        temperature, humidity, voltage, current, power, status
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    timestamp, mac_id, 'H100', device_name,
                    factory_area, floor_level, 
                    json.dumps({'test': True}), json.dumps({'test': True}),
                    25.0 + i, 60.0 + i, 220.0 + i, 5.0 + i, 1100.0 + i*50, 'normal'
                ))
            
            print(f"✅ 已處理設備: {device_name} ({mac_id}) - {factory_area} {floor_level}")
        
        conn.commit()
        
        # 檢查結果
        print(f"\n=== 檢查 device_info 表 ===")
        cursor.execute('SELECT mac_id, device_name, factory_area, floor_level FROM device_info')
        device_rows = cursor.fetchall()
        for row in device_rows:
            print(f"MAC: {row[0]}, 名稱: {row[1]}, 廠區: {row[2]}, 樓層: {row[3]}")
        
        print(f"\n=== 檢查 uart_data 表的廠區 ===")
        cursor.execute('SELECT DISTINCT factory_area FROM uart_data WHERE factory_area IS NOT NULL AND factory_area != ""')
        factory_areas = cursor.fetchall()
        print('廠區:', [area[0] for area in factory_areas])
        
        print(f"\n=== 檢查 uart_data 表的樓層 ===")
        cursor.execute('SELECT DISTINCT floor_level FROM uart_data WHERE floor_level IS NOT NULL AND floor_level != ""')
        floor_levels = cursor.fetchall()
        print('樓層:', [floor[0] for floor in floor_levels])
        
        print(f"\n=== 檢查 uart_data 表的 MAC ID ===")
        cursor.execute('SELECT DISTINCT mac_id FROM uart_data WHERE mac_id IS NOT NULL AND mac_id != ""')
        mac_ids = cursor.fetchall()
        print('MAC IDs:', [mac[0] for mac in mac_ids])
        
        conn.close()
        print("\n✅ 設備資料同步完成！")
        
    except Exception as e:
        print(f"❌ 同步失敗: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    print("🔄 開始同步設備設定到資料庫...")
    add_test_device_with_location()
