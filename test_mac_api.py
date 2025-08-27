#!/usr/bin/env python3
"""
測試 MAC ID API 的數據提取邏輯
"""

import sys
import os
sys.path.append('.')

from dashboard import get_uart_data_from_files
import json

def test_get_uart_data_from_files():
    print('=== 測試 get_uart_data_from_files 函數 ===')
    result = get_uart_data_from_files()
    print('函數返回結果:')
    print(json.dumps(result, indent=2, ensure_ascii=False))

    if result.get('success') and result.get('data'):
        print(f'\n=== 數據統計 ===')
        data = result['data']
        print(f'總通道群組數: {len(data)}')
        
        all_mac_ids = []
        for channel_data in data:
            mac_id = channel_data.get('mac_id')
            channel = channel_data.get('channel', '?')
            data_count = len(channel_data.get('data', []))
            
            if mac_id and mac_id != 'N/A':
                all_mac_ids.append(mac_id)
            
            print(f'通道 {channel} - MAC ID: {mac_id} - 數據點數: {data_count}')
        
        unique_mac_ids = list(set(all_mac_ids))
        print(f'\n找到的唯一 MAC IDs: {unique_mac_ids}')
        print(f'總 MAC ID 數量: {len(unique_mac_ids)}')
        
        # 測試 API 邏輯
        print(f'\n=== 模擬 API 處理邏輯 ===')
        flat_data = []
        for channel_data in data:
            for data_point in channel_data.get('data', []):
                flat_data.append({
                    'mac_id': channel_data.get('mac_id', 'N/A'),
                    'channel': channel_data.get('channel', 0),
                    'timestamp': data_point.get('timestamp'),
                    'parameter': data_point.get('parameter'),
                    'unit': channel_data.get('unit', 'N/A')
                })
        
        print(f'展平後的數據記錄數: {len(flat_data)}')
        
        # 提取 MAC ID（模擬 API 中的邏輯）
        mac_ids = []
        valid_mac_count = 0
        
        for entry in flat_data:
            mac_id = entry.get('mac_id')
            if mac_id and mac_id not in ['N/A', '', None]:
                mac_ids.append(mac_id)
                valid_mac_count += 1
        
        # 去重複並排序
        unique_mac_ids_from_api = sorted(list(set(mac_ids)))
        
        print(f'API 邏輯結果:')
        print(f'- 有效 MAC 記錄數: {valid_mac_count}')
        print(f'- 唯一 MAC ID 數量: {len(unique_mac_ids_from_api)}')
        print(f'- 唯一 MAC IDs: {unique_mac_ids_from_api}')
    else:
        print('未獲取到有效數據')
        print('錯誤信息:', result.get('error', '未知錯誤'))

if __name__ == "__main__":
    test_get_uart_data_from_files()
