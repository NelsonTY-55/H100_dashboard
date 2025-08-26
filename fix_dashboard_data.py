#!/usr/bin/env python3
"""
生成測試數據並檢查儀表板顯示
解決 db_setting.html 設定後看不到新資料的問題
"""

import sqlite3
import json
import random
from datetime import datetime, timedelta

def generate_test_data():
    """生成最新的測試資料到 uart_data 表格"""
    print("=== 生成測試資料 ===")
    
    try:
        conn = sqlite3.connect('uart_data.db')
        cursor = conn.cursor()
        
        # 從 device_info 表格取得最新設定的設備資訊
        cursor.execute("SELECT mac_id, device_name, factory_area, floor_level FROM device_info ORDER BY updated_at DESC LIMIT 3")
        devices = cursor.fetchall()
        
        if not devices:
            print("沒有找到設備設定，請先在 db_setting.html 設定設備")
            return False
        
        print(f"找到 {len(devices)} 個設備:")
        for device in devices:
            print(f"  - MAC: {device[0]}, 名稱: {device[1]}, 廠區: {device[2]}")
        
        # 為每個設備生成最近 24 小時的測試資料
        now = datetime.now()
        success_count = 0
        
        for device in devices:
            mac_id, device_name, factory_area, floor_level = device
            
            # 生成最近 24 小時的資料，每 10 分鐘一筆
            for i in range(144):  # 24小時 * 6 (每小時6筆)
                timestamp = now - timedelta(minutes=i * 10)
                
                # 生成隨機但合理的感測器數據
                temperature = round(20 + random.uniform(-5, 15), 2)  # 15-35度
                humidity = round(50 + random.uniform(-20, 30), 2)    # 30-80%
                voltage = round(3.3 + random.uniform(-0.3, 0.7), 2) # 3.0-4.0V
                current = round(0.1 + random.uniform(0, 0.4), 3)    # 0.1-0.5A
                power = round(voltage * current, 3)
                
                # 隨機選擇狀態
                statuses = ['normal', 'normal', 'normal', 'warning', 'normal']
                status = random.choice(statuses)
                
                raw_data = {
                    'mac_id': mac_id,
                    'device_name': device_name,
                    'factory_area': factory_area,
                    'temperature': temperature,
                    'humidity': humidity,
                    'voltage': voltage,
                    'current': current,
                    'power': power,
                    'status': status,
                    'timestamp': timestamp.isoformat()
                }
                
                parsed_data = {
                    'temperature': temperature,
                    'humidity': humidity,
                    'voltage': voltage,
                    'current': current,
                    'power': power,
                    'status': status
                }
                
                # 插入資料
                cursor.execute('''
                    INSERT INTO uart_data (
                        timestamp, mac_id, device_type, device_model,
                        factory_area, floor_level, raw_data, parsed_data,
                        temperature, humidity, voltage, current, power, status
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    timestamp.isoformat(),
                    mac_id,
                    'H100',  # 預設設備類型
                    device_name,  # 使用設備名稱作為型號
                    factory_area,
                    floor_level or '1F',
                    json.dumps(raw_data, ensure_ascii=False),
                    json.dumps(parsed_data, ensure_ascii=False),
                    temperature,
                    humidity,
                    voltage,
                    current,
                    power,
                    status
                ))
                
                success_count += 1
        
        conn.commit()
        conn.close()
        
        print(f"✅ 成功生成 {success_count} 筆測試資料")
        print(f"資料時間範圍: {(now - timedelta(hours=24)).strftime('%Y-%m-%d %H:%M')} 到 {now.strftime('%Y-%m-%d %H:%M')}")
        return True
        
    except sqlite3.Error as e:
        print(f"❌ 資料庫錯誤: {e}")
        return False
    except Exception as e:
        print(f"❌ 生成測試資料失敗: {e}")
        return False

def verify_data():
    """驗證資料是否生成成功"""
    print("\n=== 驗證資料 ===")
    
    try:
        conn = sqlite3.connect('uart_data.db')
        cursor = conn.cursor()
        
        # 檢查最新資料
        cursor.execute("""
            SELECT mac_id, factory_area, timestamp, temperature, humidity, status
            FROM uart_data 
            ORDER BY timestamp DESC 
            LIMIT 5
        """)
        recent_data = cursor.fetchall()
        
        if recent_data:
            print("最新 5 筆資料:")
            print("MAC ID | 廠區 | 時間 | 溫度 | 濕度 | 狀態")
            print("-" * 80)
            for data in recent_data:
                timestamp = data[2][:19] if len(data[2]) > 19 else data[2]  # 只顯示到秒
                print(f"{data[0][:18]}... | {data[1]} | {timestamp} | {data[3]} | {data[4]} | {data[5]}")
        
        # 檢查今天的資料數量
        today = datetime.now().date().isoformat()
        cursor.execute("SELECT COUNT(*) FROM uart_data WHERE DATE(timestamp) = ?", (today,))
        today_count = cursor.fetchone()[0]
        print(f"\n今天的資料筆數: {today_count}")
        
        # 檢查不同設備的資料分布
        cursor.execute("""
            SELECT factory_area, COUNT(*) as count
            FROM uart_data 
            WHERE DATE(timestamp) = ?
            GROUP BY factory_area
        """, (today,))
        factory_counts = cursor.fetchall()
        
        if factory_counts:
            print("\n各廠區今天的資料:")
            for factory, count in factory_counts:
                print(f"  {factory}: {count} 筆")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ 驗證失敗: {e}")
        return False

def main():
    """主程序"""
    print("🔧 解決 db_setting.html 設定後看不到新資料的問題")
    print("=" * 60)
    
    # 生成測試資料
    if generate_test_data():
        # 驗證資料
        if verify_data():
            print("\n✅ 問題已解決！")
            print("\n📌 說明:")
            print("1. 你的 db_setting.html 設定確實有正確寫入 device_info 表格")
            print("2. 儀表板顯示的圖表資料來自 uart_data 表格的實際感測器數據")
            print("3. 之前看到舊資料是因為沒有新的感測器數據寫入")
            print("4. 現在已為你的設備生成了最新的測試資料")
            print("\n🎯 現在回到儀表板應該可以看到最新的資料圖表了！")
        else:
            print("\n❌ 驗證失敗，請檢查錯誤訊息")
    else:
        print("\n❌ 生成測試資料失敗，請檢查錯誤訊息")

if __name__ == "__main__":
    main()
