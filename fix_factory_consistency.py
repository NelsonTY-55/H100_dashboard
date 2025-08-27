#!/usr/bin/env python3
"""
修正廠區名稱一致性
"""

import sqlite3

def fix_factory_area_consistency():
    """修正廠區名稱使其在所有地方保持一致"""
    
    target_mac = "0013A20042537F54"
    correct_factory_area = "L3C"
    
    print(f"修正設備 {target_mac} 的廠區名稱為 {correct_factory_area}...")
    
    try:
        conn = sqlite3.connect("uart_data.db")
        cursor = conn.cursor()
        
        # 更新 device_info 表
        cursor.execute("""
            UPDATE device_info 
            SET factory_area = ?
            WHERE mac_id = ?
        """, (correct_factory_area, target_mac))
        
        device_info_updated = cursor.rowcount
        
        # 更新 uart_data 表
        cursor.execute("""
            UPDATE uart_data 
            SET factory_area = ?
            WHERE mac_id = ?
        """, (correct_factory_area, target_mac))
        
        uart_data_updated = cursor.rowcount
        
        conn.commit()
        conn.close()
        
        print(f"✅ 已更新 device_info 表: {device_info_updated} 筆")
        print(f"✅ 已更新 uart_data 表: {uart_data_updated} 筆")
        
        return True
        
    except Exception as e:
        print(f"❌ 更新失敗: {e}")
        return False

if __name__ == "__main__":
    if fix_factory_area_consistency():
        print("廠區名稱一致性修正完成！")
    else:
        print("修正失敗！")
