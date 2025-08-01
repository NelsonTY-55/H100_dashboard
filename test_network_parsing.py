#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
網路資訊切割解析測試
演示改進後的 WiFi 網路資訊切割和顯示功能
"""

import json
import logging
from datetime import datetime

# 設定日誌格式
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('test_network_parsing.log', encoding='utf-8')
    ]
)

def test_network_parsing():
    """測試網路資訊切割解析功能"""
    
    # 模擬從實際掃描獲得的網路資料
    test_wifi_networks = [
        {
            'ssid': '2803',
            'signal': '85%', 
            'security': 'WPA2-Personal',
            'status': 'available'
        },
        {
            'ssid': 'YEE',
            'signal': '72%',
            'security': 'WPA2-Personal', 
            'status': 'available'
        },
        {
            'ssid': 'Daniel HH',
            'signal': '68%',
            'security': 'WPA2-Personal',
            'status': 'available'
        },
        {
            'ssid': 'OpenWiFi_Test',
            'signal': '45%',
            'security': 'Open',
            'status': 'available'
        },
        {
            'ssid': 'Home_Network_5G',
            'signal': '92%',
            'security': 'WPA3-Personal',
            'status': 'available'
        }
    ]
    
    # 模擬當前連接的網路
    current_wifi_info = {
        'ssid': '2803',
        'signal': '85%',
        'security': 'WPA2-Personal',
        'status': 'connected'
    }
    
    print("=" * 80)
    print("網路資訊切割解析測試")
    print("=" * 80)
    
    # 測試WiFi掃描結果切割
    test_wifi_scan_parsing(test_wifi_networks)
    
    print("\n" + "=" * 80)
    
    # 測試當前WiFi資訊切割
    test_current_wifi_parsing(current_wifi_info)
    
    print("\n" + "=" * 80)
    
    # 測試WiFi連接過程切割
    test_wifi_connection_parsing('2803', 'test_password')

def test_wifi_scan_parsing(wifi_networks):
    """測試WiFi掃描結果的切割解析"""
    print("測試 1: WiFi掃描結果切割解析")
    print("-" * 50)
    
    logging.info(f"WiFi掃描完成，找到 {len(wifi_networks)} 個網路")
    
    # 詳細記錄每個獨到的網路資訊
    for i, network in enumerate(wifi_networks, 1):
        ssid = network.get('ssid', 'Unknown')
        signal = network.get('signal', 'Unknown')
        security = network.get('security', 'Unknown')
        status = network.get('status', 'Unknown')
        
        # 切割並顯示每個網路的詳細資訊
        logging.info(f"[網路 {i:02d}] ==================")
        logging.info(f"  └─ SSID: '{ssid}'")
        logging.info(f"  └─ 信號強度: {signal}")
        logging.info(f"  └─ 安全性: {security}")
        logging.info(f"  └─ 狀態: {status}")
        
        # 如果是特定的網路，標記為重點關注
        if ssid in ['2803', 'YEE', 'Daniel HH']:
            logging.info(f"  ★ 重點網路: {ssid} - 信號強度 {signal}")
        
        # 記錄完整的網路資訊字典（用於調試）
        logging.debug(f"  └─ 完整資訊: {network}")
    
    if wifi_networks:
        logging.info("=" * 50)
        logging.info(f"網路掃描摘要: 共找到 {len(wifi_networks)} 個可用網路")
        
        # 輔助函數：從信號字串中提取百分比數值
        def get_signal_percentage(signal_str):
            try:
                if '%' in signal_str:
                    return int(signal_str.replace('%', ''))
                return 0
            except (ValueError, TypeError):
                return 0
        
        # 按信號強度分類
        strong_networks = [n for n in wifi_networks if get_signal_percentage(n.get('signal', '0%')) >= 70]
        medium_networks = [n for n in wifi_networks if 40 <= get_signal_percentage(n.get('signal', '0%')) < 70]
        weak_networks = [n for n in wifi_networks if get_signal_percentage(n.get('signal', '0%')) < 40]
        
        logging.info(f"  ├─ 強信號網路 (≥70%): {len(strong_networks)} 個")
        logging.info(f"  ├─ 中等信號網路 (40-69%): {len(medium_networks)} 個")
        logging.info(f"  └─ 弱信號網路 (<40%): {len(weak_networks)} 個")
        
        # 安全性分布
        open_networks = [n for n in wifi_networks if 'open' in n.get('security', '').lower()]
        secure_networks = [n for n in wifi_networks if 'open' not in n.get('security', '').lower()]
        
        logging.info(f"  ├─ 開放網路: {len(open_networks)} 個")
        logging.info(f"  └─ 加密網路: {len(secure_networks)} 個")
        logging.info("=" * 50)
    else:
        logging.warning("未找到任何可用的WiFi網路")

def test_current_wifi_parsing(current_wifi_info):
    """測試當前WiFi資訊的切割解析"""
    print("測試 2: 當前WiFi資訊切割解析")
    print("-" * 50)
    
    logging.info("開始獲取當前WiFi連接資訊...")
    
    # 詳細切割並記錄當前WiFi資訊
    if current_wifi_info:
        ssid = current_wifi_info.get('ssid', 'Unknown')
        signal = current_wifi_info.get('signal', 'Unknown')
        security = current_wifi_info.get('security', 'Unknown')
        status = current_wifi_info.get('status', 'Unknown')
        
        logging.info("=" * 60)
        logging.info("當前WiFi連接詳細資訊")
        logging.info("=" * 60)
        logging.info(f"  ◆ 網路名稱 (SSID): '{ssid}'")
        logging.info(f"  ◆ 信號強度: {signal}")
        logging.info(f"  ◆ 安全性類型: {security}")
        logging.info(f"  ◆ 連接狀態: {status}")
        
        # 特殊處理已知的重要網路
        if ssid == '2803':
            logging.info(f"  ★ 已連接到指定網路: {ssid}")
            logging.info(f"  ★ 網路品質: {signal}")
        elif ssid in ['YEE', 'Daniel HH']:
            logging.info(f"  ★ 已連接到重點網路: {ssid}")
        
        # 分析信號品質
        def get_signal_quality(signal_str):
            try:
                if '%' in signal_str:
                    percentage = int(signal_str.replace('%', ''))
                    if percentage >= 80:
                        return "優秀"
                    elif percentage >= 60:
                        return "良好"
                    elif percentage >= 40:
                        return "普通"
                    else:
                        return "較弱"
            except:
                return "未知"
            return "未知"
        
        signal_quality = get_signal_quality(signal)
        logging.info(f"  ◆ 信號品質評級: {signal_quality}")
        
        # 分析安全性等級
        if 'WPA3' in security.upper():
            security_level = "最高安全性"
        elif 'WPA2' in security.upper():
            security_level = "高安全性"
        elif 'WPA' in security.upper():
            security_level = "中等安全性"
        elif 'WEP' in security.upper():
            security_level = "低安全性"
        elif 'OPEN' in security.upper():
            security_level = "無加密"
        else:
            security_level = "未知安全性"
        
        logging.info(f"  ◆ 安全性等級: {security_level}")
        
        # 記錄完整資訊（用於調試）
        logging.debug(f"  ◆ 完整WiFi資訊: {current_wifi_info}")
        logging.info("=" * 60)
        
    else:
        logging.warning("=" * 60)
        logging.warning("未檢測到WiFi連接")
        logging.warning("  ⚠ 目前沒有連接到任何WiFi網路")
        logging.warning("  ⚠ 建議檢查網路設定或掃描可用網路")
        logging.warning("=" * 60)

def test_wifi_connection_parsing(ssid, password):
    """測試WiFi連接過程的切割解析"""
    print("測試 3: WiFi連接過程切割解析")
    print("-" * 50)
    
    # 詳細記錄連接請求資訊
    logging.info("=" * 60)
    logging.info("WiFi連接請求處理")
    logging.info("=" * 60)
    logging.info(f"  ◆ 目標網路 (SSID): '{ssid}'")
    logging.info(f"  ◆ 密碼長度: {len(password)} 字元" if password else "  ◆ 密碼: 無 (開放網路)")
    logging.info(f"  ◆ 請求時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 特殊網路標記
    if ssid == '2803':
        logging.info("  ★ 正在連接到指定的重要網路: 2803")
    elif ssid in ['YEE', 'Daniel HH']:
        logging.info(f"  ★ 正在連接到重點網路: {ssid}")
    
    logging.info("  ◆ 開始WiFi連接程序...")
    
    # 模擬連接成功
    success = True  # 模擬連接成功
    
    if success:
        logging.info(f"  ✓ WiFi連接成功: {ssid}")
        logging.info("  ◆ 等待網路穩定中...")
        logging.info("  ◆ 檢查網路連接狀態...")
        
        # 模擬網路狀態檢查
        network_status = {
            'internet_available': True,
            'local_network_available': True,
            'default_gateway': '192.168.1.1'
        }
        
        # 切割並顯示網路狀態詳情
        internet_available = network_status.get('internet_available', False)
        local_network_available = network_status.get('local_network_available', False)
        default_gateway = network_status.get('default_gateway', 'Unknown')
        
        logging.info("  ◆ 連接後網路狀態:")
        logging.info(f"    ├─ 網際網路連接: {'可用' if internet_available else '不可用'}")
        logging.info(f"    ├─ 本地網路連接: {'可用' if local_network_available else '不可用'}")
        logging.info(f"    └─ 預設網關: {default_gateway}")
        
        if ssid == '2803':
            logging.info(f"  ★ 成功連接到目標網路 2803，網路狀態正常")
        
        logging.info("=" * 60)
    else:
        logging.error(f"  ✗ WiFi連接失敗: {ssid}")
        logging.error("  ◆ 可能的原因:")
        logging.error("    ├─ 密碼錯誤")
        logging.error("    ├─ 網路不可用")
        logging.error("    ├─ 信號太弱")
        logging.error("    └─ 網路設定問題")
        logging.info("=" * 60)

if __name__ == "__main__":
    test_network_parsing()
    print("\n" + "=" * 80)
    print("網路資訊切割解析測試完成")
    print("詳細日誌已保存到 test_network_parsing.log")
    print("=" * 80)
