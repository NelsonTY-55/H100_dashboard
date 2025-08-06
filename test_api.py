#!/usr/bin/env python3
# 測試 dashboard API 數據

import requests
import json

try:
    print("🔍 測試 Dashboard API...")
    
    # 測試 API 端點
    url = "http://localhost:5001/api/dashboard/chart-data"
    params = {
        'mac_id': '0013A20042537F54',
        'limit': 50000
    }
    
    response = requests.get(url, params=params, timeout=10)
    print(f"📡 狀態碼: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ API 成功: {data.get('success')}")
        print(f"📊 數據通道數: {len(data.get('data', []))}")
        print(f"🕒 時間窗口: {data.get('time_window', 'N/A')}")
        print(f"📈 總數據點: {data.get('total_data_points', 0)}")
        
        if data.get('data'):
            print("\n📋 通道詳情:")
            for i, channel in enumerate(data['data'][:5]):  # 只顯示前5個通道
                ch_num = channel.get('channel')
                data_points = len(channel.get('data', []))
                unit = channel.get('unit', 'N/A')
                mac_id = channel.get('mac_id', 'N/A')
                
                print(f"  通道 {ch_num} ({unit}): {data_points} 筆數據 [MAC: {mac_id}]")
                
                if data_points > 0:
                    # 顯示最新的幾筆數據
                    recent_data = channel['data'][-3:]  # 最新3筆
                    for point in recent_data:
                        timestamp = point.get('timestamp', 'N/A')
                        parameter = point.get('parameter', 0)
                        print(f"    {timestamp}: {parameter} {unit}")
                else:
                    print("    ⚠️  無數據點")
        else:
            print("❌ 沒有數據返回!")
            print("完整回應:")
            print(json.dumps(data, indent=2, ensure_ascii=False))
    else:
        print(f"❌ API 失敗: {response.status_code}")
        print(f"回應: {response.text}")
        
except requests.exceptions.ConnectionError:
    print("❌ 無法連接到服務器 - 請確認 dashboard.py 正在運行")
except Exception as e:
    print(f"❌ 測試失敗: {e}")
