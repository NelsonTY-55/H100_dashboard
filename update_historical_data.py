#!/usr/bin/env python3
"""
更新歷史數據中的設備資訊
將 MAC ID 0013A20042537F54 的歷史數據更新為正確的廠區和樓層
"""

import sqlite3
import os
from datetime import datetime

def update_historical_data():
    """更新 uart_data 表中的歷史數據"""
    
    db_path = "uart_data.db"
    target_mac = "0013A20042537F54"
    
    if not os.path.exists(db_path):
        print(f"資料庫檔案 {db_path} 不存在")
        return False
    
    try:
        # 連接資料庫
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 檢查當前數據
        cursor.execute("""
            SELECT COUNT(*) as count, 
                   MIN(timestamp) as earliest, 
                   MAX(timestamp) as latest,
                   factory_area,
                   floor_level,
                   device_model
            FROM uart_data 
            WHERE mac_id = ?
            GROUP BY factory_area, floor_level, device_model
        """, (target_mac,))
        
        results = cursor.fetchall()
        
        print(f"MAC ID {target_mac} 的當前歷史數據:")
        for row in results:
            count, earliest, latest, factory, floor, model = row
            print(f"  {count} 筆 - 廠區: {factory}, 樓層: {floor}, 型號: {model}")
            print(f"    時間範圍: {earliest} 到 {latest}")
        
        # 更新數據
        print(f"\n正在更新 MAC ID {target_mac} 的歷史數據...")
        
        cursor.execute("""
            UPDATE uart_data 
            SET factory_area = ?, 
                floor_level = ?, 
                device_model = ?
            WHERE mac_id = ?
        """, ("L3C", "4F", "H100-001", target_mac))
        
        updated_rows = cursor.rowcount
        
        # 提交變更
        conn.commit()
        
        print(f"已更新 {updated_rows} 筆歷史數據")
        
        # 驗證更新結果
        cursor.execute("""
            SELECT COUNT(*) as count,
                   factory_area,
                   floor_level, 
                   device_model
            FROM uart_data 
            WHERE mac_id = ?
            GROUP BY factory_area, floor_level, device_model
        """, (target_mac,))
        
        results = cursor.fetchall()
        print(f"\n更新後的數據:")
        for row in results:
            count, factory, floor, model = row
            print(f"  {count} 筆 - 廠區: {factory}, 樓層: {floor}, 型號: {model}")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"更新歷史數據時發生錯誤: {e}")
        return False

if __name__ == "__main__":
    print("開始更新歷史數據...")
    
    if update_historical_data():
        print("歷史數據更新完成！")
    else:
        print("歷史數據更新失敗！")
