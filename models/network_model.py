"""
網路模型
處理網路連接和狀態管理
"""

import os
import json
import logging
import subprocess
import platform
from typing import Dict, Any, List, Optional


class NetworkModel:
    """網路模型"""
    
    def __init__(self):
        self.current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.config_file = os.path.join(self.current_dir, 'config.json')
    
    def test_connection(self, host: str = "8.8.8.8", timeout: int = 5) -> Dict[str, Any]:
        """測試網路連接"""
        try:
            # 根據作業系統選擇ping命令
            if platform.system().lower() == "windows":
                cmd = f"ping -n 1 -w {timeout * 1000} {host}"
            else:
                cmd = f"ping -c 1 -W {timeout} {host}"
            
            result = subprocess.run(
                cmd.split(),
                capture_output=True,
                text=True,
                timeout=timeout + 2
            )
            
            success = result.returncode == 0
            
            return {
                'success': success,
                'host': host,
                'response_time': self._extract_ping_time(result.stdout) if success else None,
                'output': result.stdout,
                'error': result.stderr if not success else None
            }
            
        except subprocess.TimeoutExpired:
            return {
                'success': False,
                'host': host,
                'error': f'連接測試逾時 ({timeout}s)'
            }
        except Exception as e:
            logging.error(f"測試網路連接時發生錯誤: {e}")
            return {
                'success': False,
                'host': host,
                'error': str(e)
            }
    
    def _extract_ping_time(self, ping_output: str) -> Optional[float]:
        """從ping輸出中提取響應時間"""
        try:
            lines = ping_output.split('\n')
            for line in lines:
                if 'time=' in line:
                    # 提取時間值
                    time_part = line.split('time=')[1].split('ms')[0]
                    return float(time_part)
                elif 'time<' in line:
                    # 處理 "time<1ms" 的情況
                    return 0.5
            return None
        except Exception:
            return None
    
    def get_network_status(self) -> Dict[str, Any]:
        """獲取網路狀態"""
        try:
            # 測試多個主機的連接
            test_hosts = ['8.8.8.8', '1.1.1.1', 'google.com']
            results = []
            
            for host in test_hosts:
                result = self.test_connection(host, timeout=3)
                results.append({
                    'host': host,
                    'success': result['success'],
                    'response_time': result.get('response_time'),
                    'error': result.get('error')
                })
            
            # 判斷整體網路狀態
            successful_tests = sum(1 for r in results if r['success'])
            
            if successful_tests >= 2:
                status = 'online'
            elif successful_tests == 1:
                status = 'limited'
            else:
                status = 'offline'
            
            return {
                'status': status,
                'tests': results,
                'successful_tests': successful_tests,
                'total_tests': len(test_hosts)
            }
            
        except Exception as e:
            logging.error(f"獲取網路狀態時發生錯誤: {e}")
            return {
                'status': 'error',
                'error': str(e)
            }
    
    def scan_wifi_networks(self) -> List[Dict[str, Any]]:
        """掃描可用的WiFi網路"""
        try:
            if platform.system().lower() == "windows":
                return self._scan_wifi_windows()
            else:
                return self._scan_wifi_linux()
        except Exception as e:
            logging.error(f"掃描WiFi網路時發生錯誤: {e}")
            return []
    
    def _scan_wifi_windows(self) -> List[Dict[str, Any]]:
        """Windows系統WiFi掃描"""
        try:
            result = subprocess.run(
                ['netsh', 'wlan', 'show', 'profiles'],
                capture_output=True,
                text=True,
                encoding='utf-8'
            )
            
            networks = []
            lines = result.stdout.split('\n')
            
            for line in lines:
                if 'All User Profile' in line:
                    ssid = line.split(':')[1].strip()
                    networks.append({
                        'ssid': ssid,
                        'signal_strength': 'Unknown',
                        'security': 'Unknown',
                        'frequency': 'Unknown'
                    })
            
            return networks
            
        except Exception as e:
            logging.error(f"Windows WiFi掃描失敗: {e}")
            return []
    
    def _scan_wifi_linux(self) -> List[Dict[str, Any]]:
        """Linux系統WiFi掃描"""
        try:
            result = subprocess.run(
                ['iwlist', 'scan'],
                capture_output=True,
                text=True
            )
            
            networks = []
            current_network = {}
            
            for line in result.stdout.split('\n'):
                line = line.strip()
                
                if 'Cell' in line and 'Address:' in line:
                    if current_network:
                        networks.append(current_network)
                    current_network = {}
                
                elif 'ESSID:' in line:
                    ssid = line.split('ESSID:')[1].strip().strip('"')
                    current_network['ssid'] = ssid
                
                elif 'Signal level=' in line:
                    signal = line.split('Signal level=')[1].split(' ')[0]
                    current_network['signal_strength'] = signal
                
                elif 'Encryption key:' in line:
                    encryption = 'Secured' if 'on' in line else 'Open'
                    current_network['security'] = encryption
                
                elif 'Frequency:' in line:
                    freq = line.split('Frequency:')[1].split(' ')[0]
                    current_network['frequency'] = freq
            
            if current_network:
                networks.append(current_network)
            
            return networks
            
        except Exception as e:
            logging.error(f"Linux WiFi掃描失敗: {e}")
            return []
    
    def connect_wifi(self, ssid: str, password: str = None) -> Dict[str, Any]:
        """連接WiFi網路"""
        try:
            if platform.system().lower() == "windows":
                return self._connect_wifi_windows(ssid, password)
            else:
                return self._connect_wifi_linux(ssid, password)
        except Exception as e:
            logging.error(f"連接WiFi時發生錯誤: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _connect_wifi_windows(self, ssid: str, password: str = None) -> Dict[str, Any]:
        """Windows WiFi連接"""
        try:
            if password:
                cmd = f'netsh wlan connect name="{ssid}" key="{password}"'
            else:
                cmd = f'netsh wlan connect name="{ssid}"'
            
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True
            )
            
            success = result.returncode == 0
            
            return {
                'success': success,
                'ssid': ssid,
                'message': result.stdout if success else result.stderr
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def _connect_wifi_linux(self, ssid: str, password: str = None) -> Dict[str, Any]:
        """Linux WiFi連接"""
        try:
            # 這裡需要根據具體的Linux系統和網路管理工具來實現
            # 例如使用 nmcli (NetworkManager)
            if password:
                cmd = f'nmcli dev wifi connect "{ssid}" password "{password}"'
            else:
                cmd = f'nmcli dev wifi connect "{ssid}"'
            
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True
            )
            
            success = result.returncode == 0
            
            return {
                'success': success,
                'ssid': ssid,
                'message': result.stdout if success else result.stderr
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_current_wifi(self) -> Dict[str, Any]:
        """獲取當前連接的WiFi資訊"""
        try:
            if platform.system().lower() == "windows":
                return self._get_current_wifi_windows()
            else:
                return self._get_current_wifi_linux()
        except Exception as e:
            logging.error(f"獲取當前WiFi資訊時發生錯誤: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _get_current_wifi_windows(self) -> Dict[str, Any]:
        """Windows獲取當前WiFi"""
        try:
            result = subprocess.run(
                ['netsh', 'wlan', 'show', 'interfaces'],
                capture_output=True,
                text=True,
                encoding='utf-8'
            )
            
            info = {}
            for line in result.stdout.split('\n'):
                if 'SSID' in line and 'BSSID' not in line:
                    info['ssid'] = line.split(':')[1].strip()
                elif 'State' in line:
                    info['state'] = line.split(':')[1].strip()
                elif 'Signal' in line:
                    info['signal'] = line.split(':')[1].strip()
            
            return {
                'success': True,
                'data': info
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def _get_current_wifi_linux(self) -> Dict[str, Any]:
        """Linux獲取當前WiFi"""
        try:
            result = subprocess.run(
                ['iwconfig'],
                capture_output=True,
                text=True
            )
            
            info = {}
            for line in result.stdout.split('\n'):
                if 'ESSID:' in line:
                    ssid = line.split('ESSID:')[1].strip().strip('"')
                    info['ssid'] = ssid
                elif 'Link Quality=' in line:
                    quality = line.split('Link Quality=')[1].split(' ')[0]
                    info['signal'] = quality
            
            return {
                'success': True,
                'data': info
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }