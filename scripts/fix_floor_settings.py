#!/usr/bin/env python3
"""
修正設備樓層設定：從資料庫同步正確的樓層設定到所有位置
"""

import json
import sqlite3
import os
from datetime import datetime

def fix_device_floor_settings():
    """修正設備樓層設定"""
    
    target_mac = "0013A20042537F54"
    
    print(f"開始修正設備 {target_mac} 的樓層設定...")
    
    # 1. 從資料庫讀取正確的設備資訊
    try:
        conn = sqlite3.connect("uart_data.db")
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT device_name, factory_area, floor_level, device_model, location_description
            FROM device_info 
            WHERE mac_id = ?
        """, (target_mac,))
        
        result = cursor.fetchone()
        if not result:
            print(f"❌ 在資料庫中找不到設備 {target_mac}")
            return False
        
        device_name, factory_area, floor_level, device_model, location_desc = result
        
        print(f"資料庫中的正確設備資訊:")
        print(f"  設備名稱: {device_name}")
        print(f"  廠區: {factory_area}")
        print(f"  樓層: {floor_level}")
        print(f"  設備型號: {device_model}")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ 讀取資料庫失敗: {e}")
        return False
    
    # 2. 更新設定檔案中的樓層資訊
    try:
        settings_file = "multi_device_settings.json"
        
        # 讀取現有設定
        if os.path.exists(settings_file):
            with open(settings_file, 'r', encoding='utf-8') as f:
                settings = json.load(f)
        else:
            print(f"❌ 設定檔案 {settings_file} 不存在")
            return False
        
        if target_mac not in settings:
            print(f"❌ 設定檔案中找不到設備 {target_mac}")
            return False
        
        # 檢查現在的設定
        current_location = settings[target_mac].get('device_location', '')
        print(f"設定檔案中當前樓層: {current_location}")
        print(f"資料庫中正確樓層: {floor_level}")
        
        if current_location != floor_level:
            # 備份原始檔案
            backup_file = f"{settings_file}.backup_floor_fix_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            with open(settings_file, 'r', encoding='utf-8') as f:
                backup_content = f.read()
            with open(backup_file, 'w', encoding='utf-8') as f:
                f.write(backup_content)
            print(f"原始設定檔已備份至: {backup_file}")
            
            # 更新樓層設定
            settings[target_mac]['device_location'] = floor_level
            settings[target_mac]['device_description'] = f"{factory_area}廠區{floor_level}設備"
            settings[target_mac]['updated_at'] = datetime.now().isoformat()
            
            # 寫入更新後的設定
            with open(settings_file, 'w', encoding='utf-8') as f:
                json.dump(settings, f, indent=2, ensure_ascii=False)
            
            print(f"✅ 設定檔案已更新: {current_location} → {floor_level}")
        else:
            print(f"✅ 設定檔案中的樓層已經正確")
        
    except Exception as e:
        print(f"❌ 更新設定檔案失敗: {e}")
        return False
    
    # 3. 檢查並更新歷史數據
    try:
        conn = sqlite3.connect("uart_data.db")
        cursor = conn.cursor()
        
        # 檢查歷史數據中的樓層不一致情況
        cursor.execute("""
            SELECT floor_level, COUNT(*) as count
            FROM uart_data 
            WHERE mac_id = ?
            GROUP BY floor_level
        """, (target_mac,))
        
        floor_counts = cursor.fetchall()
        print(f"\n歷史數據中的樓層分布:")
        total_records = 0
        incorrect_records = 0
        
        for floor, count in floor_counts:
            total_records += count
            if floor != floor_level:
                incorrect_records += count
                print(f"  {floor}: {count} 筆 ❌")
            else:
                print(f"  {floor}: {count} 筆 ✅")
        
        if incorrect_records > 0:
            print(f"\n需要更新 {incorrect_records}/{total_records} 筆歷史數據...")
            
            cursor.execute("""
                UPDATE uart_data 
                SET factory_area = ?, 
                    floor_level = ?
                WHERE mac_id = ? AND floor_level != ?
            """, (factory_area, floor_level, target_mac, floor_level))
            
            updated_rows = cursor.rowcount
            conn.commit()
            
            print(f"✅ 已更新 {updated_rows} 筆歷史數據")
        else:
            print(f"✅ 所有 {total_records} 筆歷史數據樓層都正確")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ 更新歷史數據失敗: {e}")
        return False
    
    print(f"\n✅ 設備 {target_mac} 的樓層設定修正完成！")
    return True

def verify_floor_settings():
    """驗證樓層設定修正結果"""
    target_mac = "0013A20042537F54"
    
    print(f"\n=== 驗證修正結果 ===")
    
    # 檢查設定檔案
    try:
        with open("multi_device_settings.json", 'r', encoding='utf-8') as f:
            settings = json.load(f)
        
        if target_mac in settings:
            device_settings = settings[target_mac]
            print(f"設定檔案:")
            print(f"  廠區: {device_settings.get('device_name')}")
            print(f"  樓層: {device_settings.get('device_location')}")
            print(f"  描述: {device_settings.get('device_description')}")
            print(f"  更新時間: {device_settings.get('updated_at')}")
        else:
            print(f"❌ 設定檔案中找不到設備 {target_mac}")
    except Exception as e:
        print(f"❌ 讀取設定檔案失敗: {e}")
    
    # 檢查資料庫
    try:
        conn = sqlite3.connect("uart_data.db")
        cursor = conn.cursor()
        
        # 檢查 device_info 表
        cursor.execute("""
            SELECT factory_area, floor_level, device_model
            FROM device_info 
            WHERE mac_id = ?
        """, (target_mac,))
        
        result = cursor.fetchone()
        if result:
            factory_area, floor_level, device_model = result
            print(f"資料庫 device_info:")
            print(f"  廠區: {factory_area}")
            print(f"  樓層: {floor_level}")
            print(f"  設備型號: {device_model}")
        
        # 檢查 uart_data 表
        cursor.execute("""
            SELECT factory_area, floor_level, COUNT(*) as count
            FROM uart_data 
            WHERE mac_id = ?
            GROUP BY factory_area, floor_level
            ORDER BY count DESC
        """, (target_mac,))
        
        results = cursor.fetchall()
        print(f"資料庫 uart_data:")
        for row in results:
            factory, floor, count = row
            print(f"  {count} 筆數據 - 廠區: {factory}, 樓層: {floor}")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ 讀取資料庫失敗: {e}")

if __name__ == "__main__":
    print("=== 修正設備樓層設定工具 ===")
    
    if fix_device_floor_settings():
        verify_floor_settings()
        print("\n建議：")
        print("1. 重新啟動 Flask 應用程式以載入新的設定")
        print("2. 在 Dashboard 中重新選擇該設備來確認顯示正確")
    else:
        print("修正失敗！")
