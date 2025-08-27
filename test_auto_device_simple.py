"""
測試自動設備管理功能
"""

import sys
import os

# 添加專案根目錄到 Python 路徑
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database_manager import db_manager

def test_auto_device_management():
    """測試自動設備管理功能"""
    print("🧪 測試自動設備管理功能")
    print("=" * 50)
    
    # 測試 MAC ID 列表
    test_macs = [
        "AA:BB:CC:DD:EE:01",
        "AA:BB:CC:DD:EE:02", 
        "BB:CC:DD:EE:FF:01",
        "CC:DD:EE:FF:AA:01"
    ]
    
    # 測試 UART 資料
    test_uart_data = [
        {
            "mac_id": "AA:BB:CC:DD:EE:01",
            "factory_area": "A廠區",
            "floor_level": "1F",
            "device_model": "H100-Pro",
            "temperature": 25.5,
            "current": 1.2
        },
        {
            "mac_id": "AA:BB:CC:DD:EE:02",
            "factory_area": "A廠區", 
            "floor_level": "2F",
            "device_model": "H100-Standard",
            "temperature": 26.0,
            "current": 1.1
        }
    ]
    
    print("\n📍 步驟 1: 測試自動設備發現")
    for i, mac_id in enumerate(test_macs):
        print(f"\n🔍 測試設備: {mac_id}")
        
        # 如果有對應的 UART 資料，使用它
        uart_data = test_uart_data[i] if i < len(test_uart_data) else None
        
        device_info = db_manager.auto_discover_device(mac_id, uart_data)
        
        if device_info:
            print(f"  ✅ 成功: {device_info.get('device_name', 'N/A')}")
            print(f"     位置: {device_info.get('factory_area', 'N/A')}-{device_info.get('floor_level', 'N/A')}")
            print(f"     型號: {device_info.get('device_model', 'N/A')}")
            print(f"     自動建立: {device_info.get('auto_created', False)}")
        else:
            print(f"  ❌ 失敗")
    
    print("\n📍 步驟 2: 測試設備統計")
    stats = db_manager.get_auto_device_statistics()
    print(f"\n📊 設備統計:")
    print(f"  總設備數: {stats.get('total_devices_count', 0)}")
    print(f"  自動設備數: {stats.get('auto_devices_count', 0)}")
    print(f"  手動設備數: {stats.get('manual_devices_count', 0)}")
    print(f"  活動設備數: {stats.get('active_devices_count', 0)}")
    
    print("\n📍 步驟 3: 測試 UART 資料處理")
    for uart_data in test_uart_data:
        mac_id = uart_data['mac_id']
        print(f"\n📡 處理 UART 資料: {mac_id}")
        
        success = db_manager.process_uart_data_with_auto_discovery(uart_data)
        if success:
            print(f"  ✅ UART 資料處理成功")
        else:
            print(f"  ❌ UART 資料處理失敗")
    
    print("\n🎉 測試完成!")

if __name__ == "__main__":
    try:
        test_auto_device_management()
    except Exception as e:
        print(f"❌ 測試失敗: {e}")
        import traceback
        traceback.print_exc()
