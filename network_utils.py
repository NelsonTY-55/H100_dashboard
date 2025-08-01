#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
網路工具模組
提供網路連接檢查和離線模式支援
"""

import socket
import subprocess
import platform
import logging
import re
import json
from typing import Tuple, Optional, List, Dict

class NetworkChecker:
    """網路連接檢查器"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def check_internet_connection(self, timeout: int = 5) -> bool:
        """
        檢查網際網路連接
        
        Args:
            timeout: 連接超時時間（秒）
            
        Returns:
            bool: True表示有網路連接，False表示無網路連接
        """
        try:
            # 嘗試連接到Google DNS伺服器
            socket.create_connection(("8.8.8.8", 53), timeout=timeout)
            return True
        except OSError:
            try:
                # 備用：嘗試連接到Cloudflare DNS
                socket.create_connection(("1.1.1.1", 53), timeout=timeout)
                return True
            except OSError:
                return False
    
    def check_local_network(self, timeout: int = 3) -> bool:
        """
        檢查本地網路連接（通常是路由器）
        
        Args:
            timeout: 連接超時時間（秒）
            
        Returns:
            bool: True表示本地網路正常，False表示本地網路異常
        """
        try:
            # 嘗試ping本地網關
            gateway = self.get_default_gateway()
            if gateway:
                return self.ping_host(gateway, timeout)
            return False
        except Exception as e:
            self.logger.warning(f"檢查本地網路失敗: {e}")
            return False
    
    def get_default_gateway(self) -> Optional[str]:
        """
        獲取預設網關IP地址
        
        Returns:
            str: 網關IP地址，如果獲取失敗則返回None
        """
        try:
            if platform.system() == "Windows":
                result = subprocess.run(
                    ["route", "print", "0.0.0.0"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                # 確保 stdout 不為 None
                stdout_content = result.stdout or ""
                for line in stdout_content.split('\n'):
                    if '0.0.0.0' in line and 'On-link' not in line:
                        parts = line.split()
                        if len(parts) >= 3:
                            return parts[2]
            else:
                # Linux/Mac
                result = subprocess.run(
                    ["ip", "route", "show", "default"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                # 確保 stdout 不為 None
                stdout_content = result.stdout or ""
                for line in stdout_content.split('\n'):
                    if 'default via' in line:
                        parts = line.split()
                        if len(parts) >= 3:
                            return parts[2]
        except Exception as e:
            self.logger.warning(f"獲取預設網關失敗: {e}")
        
        # 備用：常見的預設網關
        common_gateways = ["192.168.1.1", "192.168.0.1", "10.0.0.1"]
        for gateway in common_gateways:
            if self.ping_host(gateway, 1):
                return gateway
        
        return None
    
    def ping_host(self, host: str, timeout: int = 3) -> bool:
        """
        Ping指定主機
        
        Args:
            host: 主機IP或域名
            timeout: 超時時間（秒）
            
        Returns:
            bool: True表示ping成功，False表示ping失敗
        """
        try:
            if platform.system() == "Windows":
                cmd = ["ping", "-n", "1", "-w", str(timeout * 1000), host]
            else:
                cmd = ["ping", "-c", "1", "-W", str(timeout), host]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout + 2
            )
            return result.returncode == 0
        except Exception as e:
            self.logger.warning(f"Ping {host} 失敗: {e}")
            return False
    
    def get_network_status(self) -> dict:
        """
        獲取完整的網路狀態資訊
        
        Returns:
            dict: 包含各種網路狀態的字典
        """
        return {
            'internet_available': self.check_internet_connection(),
            'local_network_available': self.check_local_network(),
            'default_gateway': self.get_default_gateway(),
            'platform': platform.system()
        }
    
    def scan_wifi_networks(self) -> List[Dict[str, str]]:
        """
        掃描可用的WiFi網路
        
        Returns:
            List[Dict]: WiFi網路列表，每個包含 'ssid', 'signal', 'security' 等資訊
        """
        wifi_networks = []
        try:
            self.logger.info("開始掃描WiFi網路...")
            
            if platform.system() == "Windows":
                wifi_networks = self._scan_wifi_windows()
                
                # 如果第一次掃描沒有結果，嘗試強制刷新後再掃描
                if not wifi_networks:
                    self.logger.info("首次掃描無結果，嘗試強制刷新...")
                    self._force_wifi_refresh_windows()
                    import time
                    time.sleep(5)  # 等待刷新完成
                    wifi_networks = self._scan_wifi_windows()
                    
            elif platform.system() == "Linux":
                wifi_networks = self._scan_wifi_linux()
            elif platform.system() == "Darwin":  # macOS
                wifi_networks = self._scan_wifi_macos()
            else:
                self.logger.warning(f"不支援的系統平台: {platform.system()}")
                
            # 如果還是沒有結果，返回測試網路
            if not wifi_networks:
                self.logger.warning("無法掃描到WiFi網路，返回測試資料")
                wifi_networks = self._get_test_wifi_networks()
                
        except Exception as e:
            self.logger.error(f"WiFi掃描失敗: {e}")
            # 返回測試網路作為備用
            wifi_networks = self._get_test_wifi_networks()
        
        self.logger.info(f"最終掃描結果: {len(wifi_networks)} 個網路")
        return wifi_networks
    
    def _safe_subprocess_run(self, cmd, **kwargs):
        """安全地執行 subprocess 命令，確保 stdout 不為 None 並處理編碼問題"""
        try:
            # 如果沒有指定編碼相關參數，設置安全的預設值
            if 'encoding' not in kwargs and 'text' in kwargs and kwargs['text']:
                kwargs['encoding'] = 'utf-8'
                kwargs['errors'] = 'ignore'
                
            result = subprocess.run(cmd, **kwargs)
            # 確保 stdout 和 stderr 不為 None
            if result.stdout is None:
                result.stdout = ""
            if result.stderr is None:
                result.stderr = ""
            return result
        except (UnicodeDecodeError, UnicodeError) as e:
            self.logger.warning(f"編碼錯誤，使用備用方式: {e}")
            # 如果出現編碼錯誤，嘗試使用忽略錯誤的方式重新執行
            try:
                kwargs_copy = kwargs.copy()
                kwargs_copy['encoding'] = 'utf-8'
                kwargs_copy['errors'] = 'ignore'
                result = subprocess.run(cmd, **kwargs_copy)
                if result.stdout is None:
                    result.stdout = ""
                if result.stderr is None:
                    result.stderr = ""
                return result
            except Exception as fallback_e:
                self.logger.error(f"備用執行也失敗: {fallback_e}")
                # 返回模擬的失敗結果
                class MockResult:
                    def __init__(self):
                        self.returncode = 1
                        self.stdout = ""
                        self.stderr = str(fallback_e)
                return MockResult()
        except Exception as e:
            self.logger.error(f"執行命令失敗: {cmd}, 錯誤: {e}")
            # 返回一個模擬的失敗結果
            class MockResult:
                def __init__(self):
                    self.returncode = 1
                    self.stdout = ""
                    self.stderr = str(e)
            return MockResult()
    
    def _force_wifi_refresh_windows(self):
        """強制刷新Windows WiFi掃描"""
        try:
            # 嘗試多種方法來刷新WiFi掃描
            commands = [
                ["netsh", "wlan", "show", "scan"],
                ["netsh", "interface", "set", "interface", "Wi-Fi", "disable"],
                ["netsh", "interface", "set", "interface", "Wi-Fi", "enable"],
            ]
            
            for cmd in commands:
                try:
                    subprocess.run(cmd, capture_output=True, timeout=10)
                    import time
                    time.sleep(2)
                except:
                    continue
                    
        except Exception as e:
            self.logger.warning(f"WiFi刷新失敗: {e}")
    
    def _get_test_wifi_networks(self) -> List[Dict[str, str]]:
        """獲取測試用的WiFi網路列表（用於除錯）"""
        return [
            {
                'ssid': 'TestNetwork_Open',
                'signal': '85%',
                'security': 'Open',
                'status': 'test'
            },
            {
                'ssid': 'TestNetwork_WPA2',
                'signal': '70%',
                'security': 'WPA2-Personal',
                'status': 'test'
            },
            {
                'ssid': 'MyHome_WiFi',
                'signal': '60%',
                'security': 'WPA2-Personal',
                'status': 'test'
            }
        ]
    
    def _scan_wifi_windows(self) -> List[Dict[str, str]]:
        """Windows WiFi掃描"""
        networks = []
        try:
            self.logger.info("開始Windows WiFi掃描...")
            
            # 先刷新WiFi掃描
            refresh_result = self._safe_subprocess_run(
                ["netsh", "wlan", "show", "scan"],
                capture_output=True,
                text=True,
                encoding='utf-8',  # 改用UTF-8編碼
                errors='ignore',   # 忽略編碼錯誤
                timeout=20
            )
            
            self.logger.info(f"WiFi掃描刷新結果: {refresh_result.returncode}")
            
            # 等待掃描完成
            import time
            time.sleep(3)
            
            # 獲取掃描結果
            scan_result = self._safe_subprocess_run(
                ["netsh", "wlan", "show", "scan"],
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='ignore',
                timeout=15
            )
            
            self.logger.info(f"WiFi掃描結果狀態: {scan_result.returncode}")
            
            if scan_result.returncode == 0 and scan_result.stdout:
                current_network = {}
                # 確保 stdout 不為 None 再進行 split
                stdout_content = scan_result.stdout or ""
                lines = stdout_content.split('\n')
                
                for line in lines:
                    line = line.strip()
                    
                    # 偵測SSID
                    if 'SSID' in line and ':' in line and 'BSSID' not in line:
                        # 如果有之前的網路資料，先保存
                        if current_network and 'ssid' in current_network:
                            current_network.setdefault('signal', 'unknown')
                            current_network.setdefault('security', 'unknown')
                            current_network['status'] = 'available'
                            networks.append(current_network)
                        
                        current_network = {}
                        # 處理不同的SSID格式
                        if 'SSID ' in line:
                            ssid_match = re.search(r'SSID\s+\d+\s*:\s*(.+)$', line)
                        else:
                            ssid_match = re.search(r'SSID\s*:\s*(.+)$', line)
                        
                        if ssid_match:
                            ssid = ssid_match.group(1).strip()
                            if ssid and ssid != '':
                                current_network['ssid'] = ssid
                    
                    # 偵測信號強度
                    elif ('Signal' in line or '信號' in line) and ':' in line:
                        signal_match = re.search(r':\s*(\d+)%', line)
                        if signal_match:
                            current_network['signal'] = signal_match.group(1) + '%'
                    
                    # 偵測安全性
                    elif ('Authentication' in line or '驗證' in line or 'Security' in line or '安全性' in line) and ':' in line:
                        auth_match = re.search(r':\s*(.+)$', line)
                        if auth_match:
                            security = auth_match.group(1).strip()
                            if 'Open' in security or '開放' in security or security == '':
                                current_network['security'] = 'Open'
                            else:
                                current_network['security'] = security
                
                # 處理最後一個網路
                if current_network and 'ssid' in current_network:
                    current_network.setdefault('signal', 'unknown')
                    current_network.setdefault('security', 'unknown')
                    current_network['status'] = 'available'
                    networks.append(current_network)
            
            # 如果沒有掃描到網路，嘗試使用備用方法
            if not networks:
                self.logger.info("嘗試使用備用WiFi掃描方法...")
                networks = self._scan_wifi_windows_alternative()
                
        except subprocess.TimeoutExpired:
            self.logger.error("WiFi掃描超時")
            # 嘗試備用方法
            networks = self._scan_wifi_windows_alternative()
        except Exception as e:
            self.logger.error(f"Windows WiFi掃描失敗: {e}")
            # 嘗試備用方法
            networks = self._scan_wifi_windows_alternative()
        
        self.logger.info(f"掃描到 {len(networks)} 個WiFi網路")
        return self._deduplicate_networks(networks)
    
    def _scan_wifi_windows_alternative(self) -> List[Dict[str, str]]:
        """Windows WiFi掃描的備用方法"""
        networks = []
        try:
            # 使用PowerShell命令作為備用
            powershell_cmd = '''
            Get-NetAdapter -Name "Wi-Fi*" | ForEach-Object {
                $adapter = $_
                netsh wlan show profiles | Select-String "All User Profile" | ForEach-Object {
                    $ssid = ($_ -split ":")[1].Trim()
                    Write-Output "$ssid|saved|unknown"
                }
            }
            '''
            
            result = subprocess.run(
                ["powershell", "-Command", powershell_cmd],
                capture_output=True,
                text=True,
                timeout=15
            )
            
            if result.returncode == 0:
                # 確保 stdout 不為 None
                stdout_content = result.stdout or ""
                for line in stdout_content.split('\n'):
                    line = line.strip()
                    if '|' in line:
                        parts = line.split('|')
                        if len(parts) >= 3 and parts[0]:
                            networks.append({
                                'ssid': parts[0],
                                'signal': parts[2] if parts[2] != 'unknown' else 'unknown',
                                'security': 'WPA/WEP',
                                'status': parts[1]
                            })
            
            # 如果PowerShell也失敗，使用已保存的設定檔
            if not networks:
                profile_result = subprocess.run(
                    ["netsh", "wlan", "show", "profiles"],
                    capture_output=True,
                    text=True,
                    encoding='utf-8',
                    errors='ignore',
                    timeout=10
                )
                
                if profile_result.returncode == 0:
                    # 確保 stdout 不為 None
                    stdout_content = profile_result.stdout or ""
                    for line in stdout_content.split('\n'):
                        if ('All User Profile' in line or '所有使用者設定檔' in line) and ':' in line:
                            ssid_match = re.search(r':\s*(.+)$', line.strip())
                            if ssid_match:
                                ssid = ssid_match.group(1).strip()
                                if ssid:
                                    networks.append({
                                        'ssid': ssid,
                                        'signal': 'unknown',
                                        'security': 'Saved Profile',
                                        'status': 'saved'
                                    })
                                    
        except Exception as e:
            self.logger.error(f"備用WiFi掃描方法失敗: {e}")
        
        return networks
    
    def _scan_wifi_linux(self) -> List[Dict[str, str]]:
        """Linux WiFi掃描"""
        networks = []
        try:
            # 嘗試使用 iwlist 掃描
            result = subprocess.run(
                ["sudo", "iwlist", "scan"],
                capture_output=True,
                text=True,
                timeout=15
            )
            
            if result.returncode == 0:
                current_network = {}
                # 確保 stdout 不為 None
                stdout_content = result.stdout or ""
                for line in stdout_content.split('\n'):
                    line = line.strip()
                    if 'ESSID:' in line:
                        if current_network and 'ssid' in current_network:
                            networks.append(current_network)
                        current_network = {}
                        ssid_match = re.search(r'ESSID:"(.+)"', line)
                        if ssid_match:
                            current_network['ssid'] = ssid_match.group(1)
                    elif 'Quality=' in line:
                        quality_match = re.search(r'Quality=(\d+)/(\d+)', line)
                        if quality_match:
                            quality = int(quality_match.group(1))
                            max_quality = int(quality_match.group(2))
                            signal_percent = int((quality / max_quality) * 100)
                            current_network['signal'] = f"{signal_percent}%"
                    elif 'Encryption key:' in line:
                        if 'on' in line:
                            current_network['security'] = 'WPA/WEP'
                        else:
                            current_network['security'] = 'Open'
                
                # 加入最後一個網路
                if current_network and 'ssid' in current_network:
                    networks.append(current_network)
                    
        except Exception as e:
            self.logger.error(f"Linux WiFi掃描失敗: {e}")
            
        return self._deduplicate_networks(networks)
    
    def _scan_wifi_macos(self) -> List[Dict[str, str]]:
        """macOS WiFi掃描"""
        networks = []
        try:
            # 使用 airport 命令掃描
            result = subprocess.run(
                ["/System/Library/PrivateFrameworks/Apple80211.framework/Versions/Current/Resources/airport", "-s"],
                capture_output=True,
                text=True,
                timeout=15
            )
            
            if result.returncode == 0:
                # 確保 stdout 不為 None
                stdout_content = result.stdout or ""
                lines = stdout_content.split('\n')[1:]  # 跳過標題行
                for line in lines:
                    if line.strip():
                        parts = line.split()
                        if len(parts) >= 3:
                            ssid = parts[0]
                            signal = parts[2]
                            security = 'WPA/WEP' if len(parts) > 6 and 'CC' in parts[6] else 'Open'
                            
                            networks.append({
                                'ssid': ssid,
                                'signal': signal,
                                'security': security,
                                'status': 'available'
                            })
                            
        except Exception as e:
            self.logger.error(f"macOS WiFi掃描失敗: {e}")
            
        return self._deduplicate_networks(networks)
    
    def _deduplicate_networks(self, networks: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """移除重複的WiFi網路"""
        seen_ssids = set()
        unique_networks = []
        
        for network in networks:
            ssid = network.get('ssid', '')
            if ssid and ssid not in seen_ssids:
                seen_ssids.add(ssid)
                # 設定預設值
                network.setdefault('signal', 'unknown')
                network.setdefault('security', 'unknown')
                network.setdefault('status', 'available')
                unique_networks.append(network)
        
        # 按信號強度排序
        return sorted(unique_networks, key=lambda x: self._signal_strength_sort_key(x.get('signal', '0%')), reverse=True)
    
    def _signal_strength_sort_key(self, signal: str) -> int:
        """提取信號強度用於排序"""
        try:
            if '%' in signal:
                return int(signal.replace('%', ''))
            return 0
        except (ValueError, AttributeError):
            return 0
    
    def connect_to_wifi(self, ssid: str, password: str = "") -> bool:
        """
        連接到指定的WiFi網路
        
        Args:
            ssid: WiFi網路名稱
            password: WiFi密碼（如果需要）
            
        Returns:
            bool: 連接是否成功
        """
        try:
            if platform.system() == "Windows":
                return self._connect_wifi_windows(ssid, password)
            elif platform.system() == "Linux":
                return self._connect_wifi_linux(ssid, password)
            elif platform.system() == "Darwin":
                return self._connect_wifi_macos(ssid, password)
            else:
                self.logger.warning(f"不支援的系統平台: {platform.system()}")
                return False
        except Exception as e:
            self.logger.error(f"WiFi連接失敗: {e}")
            return False
    
    def _connect_wifi_windows(self, ssid: str, password: str) -> bool:
        """Windows WiFi連接"""
        try:
            if password:
                # 建立設定檔
                profile_xml = f'''<?xml version="1.0"?>
<WLANProfile xmlns="http://www.microsoft.com/networking/WLAN/profile/v1">
    <name>{ssid}</name>
    <SSIDConfig>
        <SSID>
            <name>{ssid}</name>
        </SSID>
    </SSIDConfig>
    <connectionType>ESS</connectionType>
    <connectionMode>auto</connectionMode>
    <MSM>
        <security>
            <authEncryption>
                <authentication>WPA2PSK</authentication>
                <encryption>AES</encryption>
                <useOneX>false</useOneX>
            </authEncryption>
            <sharedKey>
                <keyType>passPhrase</keyType>
                <protected>false</protected>
                <keyMaterial>{password}</keyMaterial>
            </sharedKey>
        </security>
    </MSM>
</WLANProfile>'''
                
                # 儲存設定檔到臨時檔案
                import tempfile
                with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False, encoding='utf-8') as f:
                    f.write(profile_xml)
                    profile_path = f.name
                
                # 加入設定檔
                add_result = subprocess.run(
                    ["netsh", "wlan", "add", "profile", f"filename={profile_path}"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                # 刪除臨時檔案
                import os
                os.unlink(profile_path)
                
                if add_result.returncode != 0:
                    self.logger.error(f"加入WiFi設定檔失敗: {add_result.stderr}")
                    return False
            
            # 連接到網路
            connect_result = subprocess.run(
                ["netsh", "wlan", "connect", f"name={ssid}"],
                capture_output=True,
                text=True,
                timeout=15
            )
            
            return connect_result.returncode == 0
            
        except Exception as e:
            self.logger.error(f"Windows WiFi連接失敗: {e}")
            return False
    
    def _connect_wifi_linux(self, ssid: str, password: str) -> bool:
        """Linux WiFi連接"""
        # 這裡需要根據具體的Linux發行版實現
        # 通常使用 NetworkManager 或 wpa_supplicant
        self.logger.warning("Linux WiFi連接功能尚未完全實現")
        return False
    
    def _connect_wifi_macos(self, ssid: str, password: str) -> bool:
        """macOS WiFi連接"""
        try:
            if password:
                result = subprocess.run(
                    ["networksetup", "-setairportnetwork", "en0", ssid, password],
                    capture_output=True,
                    text=True,
                    timeout=15
                )
            else:
                result = subprocess.run(
                    ["networksetup", "-setairportnetwork", "en0", ssid],
                    capture_output=True,
                    text=True,
                    timeout=15
                )
            
            return result.returncode == 0
            
        except Exception as e:
            self.logger.error(f"macOS WiFi連接失敗: {e}")
            return False
    
    def get_current_wifi_info(self) -> Optional[Dict[str, str]]:
        """
        獲取當前連接的WiFi資訊
        
        Returns:
            Dict: 當前WiFi資訊，包含 'ssid', 'signal', 'security' 等
        """
        try:
            if platform.system() == "Windows":
                return self._get_current_wifi_windows()
            elif platform.system() == "Linux":
                return self._get_current_wifi_linux()
            elif platform.system() == "Darwin":
                return self._get_current_wifi_macos()
            else:
                self.logger.warning(f"不支援的系統平台: {platform.system()}")
                return None
        except Exception as e:
            self.logger.error(f"獲取當前WiFi資訊失敗: {e}")
            return None
    
    def _get_current_wifi_windows(self) -> Optional[Dict[str, str]]:
        """Windows 獲取當前WiFi資訊"""
        try:
            # 使用 UTF-8 編碼並忽略解碼錯誤
            result = subprocess.run(
                ["netsh", "wlan", "show", "interfaces"],
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='ignore',
                timeout=10
            )
            
            if result.returncode == 0:
                current_wifi = {}
                # 確保 stdout 不為 None
                stdout_content = result.stdout or ""
                for line in stdout_content.split('\n'):
                    line = line.strip()
                    if 'SSID' in line and ':' in line:
                        ssid_match = re.search(r': (.+)$', line)
                        if ssid_match:
                            current_wifi['ssid'] = ssid_match.group(1).strip()
                    elif '信號' in line or 'Signal' in line:
                        signal_match = re.search(r': (\d+)%', line)
                        if signal_match:
                            current_wifi['signal'] = signal_match.group(1) + '%'
                    elif '驗證' in line or 'Authentication' in line:
                        auth_match = re.search(r': (.+)$', line)
                        if auth_match:
                            current_wifi['security'] = auth_match.group(1).strip()
                
                if 'ssid' in current_wifi:
                    current_wifi['status'] = 'connected'
                    return current_wifi
                    
        except Exception as e:
            self.logger.error(f"Windows 獲取當前WiFi資訊失敗: {e}")
        
        return None
    
    def _get_current_wifi_linux(self) -> Optional[Dict[str, str]]:
        """Linux 獲取當前WiFi資訊"""
        try:
            # 使用 iwconfig 或 nmcli
            result = subprocess.run(
                ["iwconfig"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                # 確保 stdout 不為 None
                stdout_content = result.stdout or ""
                for line in stdout_content.split('\n'):
                    if 'ESSID:' in line:
                        essid_match = re.search(r'ESSID:"(.+)"', line)
                        if essid_match:
                            return {
                                'ssid': essid_match.group(1),
                                'signal': 'unknown',
                                'security': 'unknown',
                                'status': 'connected'
                            }
                            
        except Exception as e:
            self.logger.error(f"Linux 獲取當前WiFi資訊失敗: {e}")
        
        return None
    
    def _get_current_wifi_macos(self) -> Optional[Dict[str, str]]:
        """macOS 獲取當前WiFi資訊"""
        try:
            result = subprocess.run(
                ["/System/Library/PrivateFrameworks/Apple80211.framework/Versions/Current/Resources/airport", "-I"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                current_wifi = {}
                # 確保 stdout 不為 None
                stdout_content = result.stdout or ""
                for line in stdout_content.split('\n'):
                    if 'SSID:' in line:
                        ssid_match = re.search(r'SSID: (.+)$', line.strip())
                        if ssid_match:
                            current_wifi['ssid'] = ssid_match.group(1).strip()
                    elif 'agrCtlRSSI:' in line:
                        signal_match = re.search(r'agrCtlRSSI: (-?\d+)', line)
                        if signal_match:
                            # 將 RSSI 轉換為百分比
                            rssi = int(signal_match.group(1))
                            signal_percent = max(0, min(100, (rssi + 100) * 2))
                            current_wifi['signal'] = f"{signal_percent}%"
                
                if 'ssid' in current_wifi:
                    current_wifi.setdefault('signal', 'unknown')
                    current_wifi['security'] = 'unknown'
                    current_wifi['status'] = 'connected'
                    return current_wifi
                    
        except Exception as e:
            self.logger.error(f"macOS 獲取當前WiFi資訊失敗: {e}")
        
        return None

class OfflineModeManager:
    """離線模式管理器"""
    
    def __init__(self, config_manager):
        self.config_manager = config_manager
        self.network_checker = NetworkChecker()
        self.logger = logging.getLogger(__name__)
    
    def should_use_offline_mode(self) -> bool:
        """
        判斷是否應該使用離線模式
        
        Returns:
            bool: True表示應該使用離線模式
        """
        # 檢查手動設定的離線模式
        manual_offline = self.config_manager.get('offline_mode', False)
        if manual_offline:
            return True
        
        # 檢查網路連接狀態
        network_status = self.network_checker.get_network_status()
        if not network_status['internet_available']:
            self.logger.info("偵測到無網際網路連接，自動啟用離線模式")
            return True
        
        return False
    
    def enable_offline_mode(self):
        """啟用離線模式"""
        self.config_manager.set('offline_mode', True)
        self.config_manager.save_config()
        self.logger.info("已啟用離線模式")
    
    def disable_offline_mode(self):
        """停用離線模式"""
        self.config_manager.set('offline_mode', False)
        self.config_manager.save_config()
        self.logger.info("已停用離線模式")
    
    def auto_detect_mode(self) -> str:
        """
        自動偵測並設定模式
        
        Returns:
            str: 'online' 或 'offline'
        """
        if self.should_use_offline_mode():
            self.enable_offline_mode()
            return 'offline'
        else:
            return 'online'

# 建立全域實例（需要在導入時提供config_manager）
network_checker = NetworkChecker()

def create_offline_mode_manager(config_manager):
    """建立離線模式管理器實例"""
    return OfflineModeManager(config_manager)
