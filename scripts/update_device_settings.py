#!/usr/bin/env python3
"""
更新特定設備的設定檔案
用於修正 MAC ID 0013A20042537F54 的設備資訊
"""

import json
import os
from datetime import datetime

def update_device_settings():
    """更新設備設定檔案"""
    
    # 設定檔案路徑
    settings_file = "multi_device_settings.json"
    
    # 目標設備的 MAC ID
    target_mac = "0013A20042537F54"
    
    # 正確的設定值
    correct_settings = {
        "device_name": "L3C",           # 廠區
        "device_location": "4F",        # 樓層
        "device_model": {               # 設備型號 - 請根據實際情況修改
            "0": "H100-001",
            "1": "H100-002", 
            "2": "H100-003",
            "3": "H100-004"
        },
        "device_serial": target_mac,
        "device_description": "L3C廠區4樓設備",
        "redirect_to_dashboard": False,
        "updated_at": datetime.now().isoformat()
    }
    
    try:
        # 讀取現有設定
        if os.path.exists(settings_file):
            with open(settings_file, 'r', encoding='utf-8') as f:
                settings = json.load(f)
        else:
            settings = {}
        
        # 保留創建時間（如果存在）
        if target_mac in settings and 'created_at' in settings[target_mac]:
            correct_settings['created_at'] = settings[target_mac]['created_at']
        else:
            correct_settings['created_at'] = datetime.now().isoformat()
        
        # 更新設定
        settings[target_mac] = correct_settings
        
        # 備份原始檔案
        if os.path.exists(settings_file):
            backup_file = f"{settings_file}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            os.rename(settings_file, backup_file)
            print(f"原始檔案已備份至: {backup_file}")
        
        # 寫入更新後的設定
        with open(settings_file, 'w', encoding='utf-8') as f:
            json.dump(settings, f, indent=2, ensure_ascii=False)
        
        print(f"設備 {target_mac} 的設定已更新:")
        print(f"  廠區: {correct_settings['device_name']}")
        print(f"  樓層: {correct_settings['device_location']}")
        print(f"  設備型號: {correct_settings['device_model']}")
        print(f"  描述: {correct_settings['device_description']}")
        
        return True
        
    except Exception as e:
        print(f"更新設定時發生錯誤: {e}")
        return False

def update_database():
    """同步更新資料庫"""
    try:
        from database_manager import DatabaseManager
        
        db_manager = DatabaseManager()
        
        # 更新設備資訊
        device_info = {
            'mac_id': "0013A20042537F54",
            'device_name': "L3C",
            'device_type': "H100",
            'device_model': "H100-001",  # 使用主要型號
            'factory_area': "L3C",
            'floor_level': "4F",
            'location_description': "4F",
            'status': 'active'
        }
        
        success = db_manager.register_device(device_info)
        if success:
            print("資料庫設備資訊已更新")
        else:
            print("資料庫更新失敗")
            
    except Exception as e:
        print(f"更新資料庫時發生錯誤: {e}")

if __name__ == "__main__":
    print("開始更新設備設定...")
    
    # 更新設定檔案
    if update_device_settings():
        print("設定檔案更新成功")
        
        # 同步到資料庫
        print("正在同步資料庫...")
        update_database()
        
        print("設定更新完成！")
    else:
        print("設定更新失敗！")
