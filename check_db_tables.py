#!/usr/bin/env python3
"""檢查 uart_data.db 資料庫的表格和資料"""

import sqlite3
import json
from datetime import datetime

def check_database():
    """檢查資料庫狀態"""
    print("=== 檢查 uart_data.db 資料庫 ===\n")
    
    try:
        conn = sqlite3.connect('uart_data.db')
        cursor = conn.cursor()
        
        # 檢查表格
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        print("資料庫中的表格:")
        for table in tables:
            print(f"- {table[0]}")
        print()
        
        # 檢查 device_info 表格
        if any('device_info' in table for table in tables):
            print("=== device_info 表格資料 ===")
            cursor.execute("SELECT * FROM device_info ORDER BY mac_id")
            devices = cursor.fetchall()
            
            if devices:
                # 取得欄位名稱
                cursor.execute("PRAGMA table_info(device_info)")
                columns = [col[1] for col in cursor.fetchall()]
                print(f"欄位: {', '.join(columns)}")
                print()
                
                for device in devices:
                    print(f"MAC ID: {device[0]}")
                    for i, value in enumerate(device[1:], 1):
                        print(f"  {columns[i]}: {value}")
                    print()
            else:
                print("device_info 表格中沒有資料")
            print()
        
        # 檢查 uart_data 表格的最新資料
        if any('uart_data' in table for table in tables):
            print("=== uart_data 表格最新 5 筆資料 ===")
            cursor.execute("""
                SELECT mac_id, device_name, factory_area, timestamp, temperature, humidity
                FROM uart_data 
                ORDER BY timestamp DESC 
                LIMIT 5
            """)
            recent_data = cursor.fetchall()
            
            if recent_data:
                print("MAC ID | 設備名稱 | 廠區 | 時間 | 溫度 | 濕度")
                print("-" * 80)
                for data in recent_data:
                    print(f"{data[0]} | {data[1]} | {data[2]} | {data[3]} | {data[4]} | {data[5]}")
            else:
                print("uart_data 表格中沒有資料")
            print()
            
            # 檢查資料數量
            cursor.execute("SELECT COUNT(*) FROM uart_data")
            count = cursor.fetchone()[0]
            print(f"uart_data 表格總資料筆數: {count}")
            print()
        
        conn.close()
        
    except sqlite3.Error as e:
        print(f"資料庫錯誤: {e}")
    except Exception as e:
        print(f"檢查失敗: {e}")

if __name__ == "__main__":
    check_database()
