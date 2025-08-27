"""
自動設備管理器測試腳本
測試 MAC ID 動態設備發現功能
"""

import sys
import os

# 添加專案根目錄到 Python 路徑
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from auto_device_manager import auto_device_manager
from uart_auto_discovery import (
    process_uart_data_with_auto_discovery,
    get_device_info_by_mac,
    batch_discover_devices_from_uart_history,
    get_auto_device_statistics
)

def test_auto_device_discovery():
    """測試自動設備發現功能"""
    print("🧪 測試自動設備發現功能")
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
        },
        {
            "mac_id": "BB:CC:DD:EE:FF:01",
            "factory_area": "B廠區",
            "floor_level": "1F", 
            "device_model": "H100-Lite",
            "temperature": 24.8,
            "current": 1.3
        },
        {
            "mac_id": "CC:DD:EE:FF:AA:01",
            # 這個設備沒有廠區和樓層資訊，測試自動推斷
            "device_model": "H100-Unknown",
            "temperature": 25.0,
            "current": 1.0
        }
    ]
    
    print("\n📍 步驟 1: 測試自動設備發現")
    for i, mac_id in enumerate(test_macs):
        print(f"\n🔍 測試設備: {mac_id}")
        
        # 如果有對應的 UART 資料，使用它
        uart_data = test_uart_data[i] if i < len(test_uart_data) else None
        
        device_info = auto_device_manager.discover_device_from_mac(mac_id, uart_data)
        
        if device_info:
            print(f"  ✅ 成功: {device_info.get('device_name', 'N/A')}")
            print(f"     位置: {device_info.get('factory_area', 'N/A')}-{device_info.get('floor_level', 'N/A')}")
            print(f"     型號: {device_info.get('device_model', 'N/A')}")
            print(f"     狀態: {device_info.get('status', 'N/A')}")
            print(f"     自動建立: {device_info.get('auto_created', False)}")
        else:
            print(f"  ❌ 失敗")
    
    print("\n📍 步驟 2: 測試 UART 資料處理")
    for uart_data in test_uart_data:
        mac_id = uart_data['mac_id']
        print(f"\n📡 處理 UART 資料: {mac_id}")
        
        success = process_uart_data_with_auto_discovery(uart_data)
        if success:
            print(f"  ✅ UART 資料處理成功")
        else:
            print(f"  ❌ UART 資料處理失敗")
    
    print("\n📍 步驟 3: 測試設備資訊查詢")
    for mac_id in test_macs:
        print(f"\n🔎 查詢設備: {mac_id}")
        
        device_info = get_device_info_by_mac(mac_id)
        if device_info:
            print(f"  ✅ 找到設備: {device_info.get('device_name', 'N/A')}")
        else:
            print(f"  ❌ 設備不存在")
    
    print("\n📍 步驟 4: 測試統計資訊")
    stats = get_auto_device_statistics()
    print(f"\n📊 設備統計:")
    print(f"  總設備數: {stats.get('total_devices_count', 0)}")
    print(f"  自動設備數: {stats.get('auto_devices_count', 0)}")
    print(f"  手動設備數: {stats.get('manual_devices_count', 0)}")
    print(f"  活動設備數: {stats.get('active_devices_count', 0)}")
    
    print("\n📍 步驟 5: 測試批次發現")
    try:
        discovered_count = batch_discover_devices_from_uart_history()
        print(f"\n🔄 批次發現結果: 發現 {discovered_count} 個設備")
    except Exception as e:
        print(f"\n⚠️  批次發現失敗: {e}")
    
    print("\n🎉 測試完成!")
    print("=" * 50)

def test_mac_location_inference():
    """測試 MAC ID 位置推斷功能"""
    print("\n🧪 測試 MAC ID 位置推斷")
    print("=" * 50)
    
    test_cases = [
        "AA:BB:CC:DD:EE:01",  # 應該推斷為 A廠區, 2F
        "AB:BB:CC:DD:EE:12",  # 應該推斷為 B廠區, 3F
        "AC:BB:CC:DD:EE:23",  # 應該推斷為 C廠區, 4F
        "AD:BB:CC:DD:EE:34",  # 應該推斷為 A廠區, 5F
        "00:11:22:33:44:55",  # 測試數字 MAC
    ]
    
    for mac_id in test_cases:
        print(f"\n🔍 測試 MAC: {mac_id}")
        
        # 使用自動設備管理器的推斷功能
        device_info = auto_device_manager.discover_device_from_mac(mac_id)
        
        if device_info:
            factory_area = device_info.get('factory_area', 'N/A')
            floor_level = device_info.get('floor_level', 'N/A')
            device_name = device_info.get('device_name', 'N/A')
            
            print(f"  推斷結果:")
            print(f"    設備名稱: {device_name}")
            print(f"    廠區: {factory_area}")
            print(f"    樓層: {floor_level}")

def simulate_real_scenario():
    """模擬真實場景"""
    print("\n🧪 模擬真實場景 - 設備陸續上線")
    print("=" * 50)
    
    # 模擬不同時間點的設備上線
    scenarios = [
        {
            "time": "09:00",
            "description": "早班設備開始上線",
            "devices": [
                {"mac_id": "A1:B2:C3:D4:E5:01", "factory_area": "A廠區", "floor_level": "1F"},
                {"mac_id": "A1:B2:C3:D4:E5:02", "factory_area": "A廠區", "floor_level": "1F"},
            ]
        },
        {
            "time": "09:30", 
            "description": "更多設備上線，包含新設備",
            "devices": [
                {"mac_id": "B1:C2:D3:E4:F5:01", "factory_area": "B廠區", "floor_level": "2F"},
                {"mac_id": "C1:D2:E3:F4:A5:01"},  # 沒有位置資訊的新設備
            ]
        },
        {
            "time": "10:00",
            "description": "設備資料更新",
            "devices": [
                {"mac_id": "A1:B2:C3:D4:E5:01", "factory_area": "A廠區", "floor_level": "1F", "device_model": "H100-Pro-Updated"},
            ]
        }
    ]
    
    for scenario in scenarios:
        print(f"\n⏰ {scenario['time']} - {scenario['description']}")
        
        for device_data in scenario['devices']:
            mac_id = device_data['mac_id']
            print(f"  📡 處理設備: {mac_id}")
            
            # 模擬 UART 資料
            uart_data = {
                "mac_id": mac_id,
                "timestamp": f"2025-08-27T{scenario['time']}:00",
                "temperature": 25.0 + (hash(mac_id) % 10),
                "current": 1.0 + (hash(mac_id) % 5) * 0.1,
                **device_data  # 包含廠區、樓層等資訊
            }
            
            # 處理 UART 資料
            success = process_uart_data_with_auto_discovery(uart_data)
            
            if success:
                # 查詢設備資訊確認
                device_info = get_device_info_by_mac(mac_id)
                if device_info:
                    print(f"    ✅ 設備已就緒: {device_info.get('device_name', 'N/A')}")
                    print(f"       位置: {device_info.get('factory_area', 'N/A')}-{device_info.get('floor_level', 'N/A')}")
                else:
                    print(f"    ⚠️  設備處理成功但查詢失敗")
            else:
                print(f"    ❌ 設備處理失敗")
    
    # 最終統計
    print(f"\n📊 場景結束後的統計:")
    stats = get_auto_device_statistics()
    print(f"  總設備數: {stats.get('total_devices_count', 0)}")
    print(f"  自動設備數: {stats.get('auto_devices_count', 0)}")

if __name__ == "__main__":
    print("🚀 自動設備管理器測試開始")
    
    try:
        # 測試基本功能
        test_auto_device_discovery()
        
        # 測試 MAC ID 推斷
        test_mac_location_inference()
        
        # 模擬真實場景
        simulate_real_scenario()
        
        print("\n✅ 所有測試完成!")
        
    except Exception as e:
        print(f"\n❌ 測試過程中發生錯誤: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n👋 測試結束")
