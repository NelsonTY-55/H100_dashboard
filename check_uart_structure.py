#!/usr/bin/env python3
"""檢查 uart_data 表格結構"""

import sqlite3

def check_uart_data_structure():
    """檢查 uart_data 表格結構"""
    try:
        conn = sqlite3.connect('uart_data.db')
        cursor = conn.cursor()
        
        # 檢查 uart_data 表格結構
        print("=== uart_data 表格結構 ===")
        cursor.execute("PRAGMA table_info(uart_data)")
        columns = cursor.fetchall()
        
        for col in columns:
            print(f"欄位 {col[1]}: {col[2]} (PK={col[5]})")
        print()
        
        # 檢查最新的 5 筆資料
        print("=== uart_data 表格最新 5 筆資料 ===")
        cursor.execute("""
            SELECT mac_id, factory_area, timestamp, temperature, humidity, status
            FROM uart_data 
            ORDER BY timestamp DESC 
            LIMIT 5
        """)
        recent_data = cursor.fetchall()
        
        if recent_data:
            print("MAC ID | 廠區 | 時間 | 溫度 | 濕度 | 狀態")
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
        
        # 檢查不同 MAC ID 的數量
        cursor.execute("SELECT COUNT(DISTINCT mac_id) FROM uart_data")
        mac_count = cursor.fetchone()[0]
        print(f"不同 MAC ID 數量: {mac_count}")
        
        # 列出所有 MAC ID
        cursor.execute("SELECT DISTINCT mac_id FROM uart_data ORDER BY mac_id")
        mac_ids = cursor.fetchall()
        print(f"所有 MAC ID: {[mac[0] for mac in mac_ids]}")
        
        conn.close()
        
    except sqlite3.Error as e:
        print(f"資料庫錯誤: {e}")
    except Exception as e:
        print(f"檢查失敗: {e}")

if __name__ == "__main__":
    check_uart_data_structure()
