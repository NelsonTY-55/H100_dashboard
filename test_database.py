"""
資料庫功能測試腳本
測試 UART 資料儲存和查詢功能
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database_manager import db_manager
from datetime import datetime, timedelta
import json
import random

def test_database_functionality():
    """測試資料庫功能"""
    print("開始測試資料庫功能...")
    
    # 測試 1: 資料庫初始化
    print("\n1. 測試資料庫初始化...")
    try:
        print("✅ 資料庫初始化成功")
    except Exception as e:
        print(f"❌ 資料庫初始化失敗: {e}")
        return False
    
    # 測試 2: 插入測試資料
    print("\n2. 插入測試資料...")
    test_data_list = []
    
    # 生成一些測試資料
    factory_areas = ['廠區A', '廠區B', '廠區C']
    floor_levels = ['1F', '2F', '3F']
    mac_ids = ['AA:BB:CC:DD:EE:01', 'AA:BB:CC:DD:EE:02', 'AA:BB:CC:DD:EE:03']
    device_models = ['H100-001', 'H100-002', 'H200-001']
    
    base_time = datetime.now() - timedelta(hours=24)
    
    for i in range(50):  # 插入 50 筆測試資料
        test_data = {
            'timestamp': (base_time + timedelta(minutes=i*30)).isoformat(),
            'mac_id': random.choice(mac_ids),
            'device_type': 'UART Device',
            'device_model': random.choice(device_models),
            'factory_area': random.choice(factory_areas),
            'floor_level': random.choice(floor_levels),
            'raw_data': f'test_data_{i}',
            'temperature': round(random.uniform(20.0, 35.0), 2),
            'humidity': round(random.uniform(40.0, 80.0), 2),
            'voltage': round(random.uniform(220.0, 240.0), 2),
            'current': round(random.uniform(1.0, 10.0), 2),
            'power': round(random.uniform(100.0, 2000.0), 2),
            'status': random.choice(['normal', 'warning', 'error'])
        }
        
        success = db_manager.save_uart_data(test_data)
        if success:
            test_data_list.append(test_data)
        else:
            print(f"❌ 插入資料失敗: 第 {i+1} 筆")
    
    print(f"✅ 成功插入 {len(test_data_list)} 筆測試資料")
    
    # 測試 3: 查詢廠區列表
    print("\n3. 測試查詢廠區列表...")
    areas = db_manager.get_factory_areas()
    print(f"✅ 找到廠區: {areas}")
    
    # 測試 4: 查詢樓層列表
    print("\n4. 測試查詢樓層列表...")
    floors = db_manager.get_floor_levels()
    print(f"✅ 找到樓層: {floors}")
    
    # 測試 5: 查詢 MAC ID 列表
    print("\n5. 測試查詢 MAC ID 列表...")
    mac_ids_result = db_manager.get_mac_ids()
    print(f"✅ 找到 MAC ID: {mac_ids_result}")
    
    # 測試 6: 查詢設備型號列表
    print("\n6. 測試查詢設備型號列表...")
    models = db_manager.get_device_models()
    print(f"✅ 找到設備型號: {models}")
    
    # 測試 7: 查詢圖表資料
    print("\n7. 測試查詢圖表資料...")
    chart_data = db_manager.get_chart_data(
        data_type='temperature',
        limit=10
    )
    print(f"✅ 找到溫度資料: {len(chart_data)} 筆")
    if chart_data:
        print(f"   範例資料: {chart_data[0]}")
    
    # 測試 8: 查詢統計資訊
    print("\n8. 測試查詢統計資訊...")
    stats = db_manager.get_statistics()
    print(f"✅ 統計資訊: {json.dumps(stats, indent=2, ensure_ascii=False)}")
    
    # 測試 9: 註冊設備資訊
    print("\n9. 測試註冊設備資訊...")
    device_info = {
        'mac_id': 'AA:BB:CC:DD:EE:01',
        'device_name': '測試設備1',
        'device_type': 'UART Device',
        'device_model': 'H100-001',
        'factory_area': '廠區A',
        'floor_level': '1F',
        'location_description': '測試位置',
        'installation_date': datetime.now().date().isoformat(),
        'status': 'active'
    }
    
    success = db_manager.register_device(device_info)
    if success:
        print("✅ 設備註冊成功")
    else:
        print("❌ 設備註冊失敗")
    
    # 測試 10: 查詢設備資訊
    print("\n10. 測試查詢設備資訊...")
    device_list = db_manager.get_device_info()
    print(f"✅ 找到設備: {len(device_list)} 台")
    if device_list:
        print(f"   範例設備: {device_list[0]}")
    
    print("\n✅ 所有測試完成！")
    return True

def test_api_integration():
    """測試 API 整合"""
    print("\n開始測試 API 整合...")
    
    try:
        import requests
        base_url = "http://localhost:5001"
        
        # 測試 1: 廠區列表 API
        print("\n1. 測試廠區列表 API...")
        response = requests.get(f"{base_url}/api/database/factory-areas")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ API 回應: {data}")
        else:
            print(f"❌ API 請求失敗: {response.status_code}")
        
        # 測試 2: 統計資訊 API
        print("\n2. 測試統計資訊 API...")
        response = requests.get(f"{base_url}/api/database/statistics")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ API 回應: {data}")
        else:
            print(f"❌ API 請求失敗: {response.status_code}")
        
    except Exception as e:
        print(f"❌ API 測試失敗: {e}")
        print("   提示: 請確保 Dashboard 服務正在運行 (python dashboard.py)")

if __name__ == "__main__":
    print("H100 Dashboard 資料庫功能測試")
    print("=" * 50)
    
    # 測試資料庫功能
    if test_database_functionality():
        print("\n" + "=" * 50)
        print("資料庫功能測試完成！")
        
        # 測試 API 整合 (可選)
        print("\n是否要測試 API 整合？(需要 Dashboard 服務運行)")
        choice = input("輸入 'y' 開始 API 測試，其他鍵跳過: ")
        if choice.lower() == 'y':
            test_api_integration()
    
    print("\n測試完成！")
    print("您現在可以:")
    print("1. 啟動 Dashboard 服務: python dashboard.py")
    print("2. 訪問資料分析頁面: http://localhost:5001/data-analysis")
    print("3. 啟動 UART 讀取來產生真實資料")
