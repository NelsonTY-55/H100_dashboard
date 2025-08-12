"""
WiFi 管理工具
用於掃描、連接和管理 WiFi 網路
"""

import subprocess
import json
import platform
import logging
import re
import time

logger = logging.getLogger(__name__)

class WiFiManager:
    def __init__(self):
        self.system = platform.system()
        logger.info(f"WiFi 管理器初始化，系統: {self.system}")
    
    def scan_networks(self):
        """掃描可用的 WiFi 網路"""
        try:
            if self.system == "Windows":
                return self._scan_windows()
            elif self.system == "Linux":
                return self._scan_linux()
            else:
                logger.error(f"不支援的作業系統: {self.system}")
                return []
        except Exception as e:
            logger.error(f"WiFi 掃描失敗: {e}")
            return []
    
    def get_available_networks(self):
        """獲取所有可用的 WiFi 網路，格式化為易於使用的列表"""
        networks = self.scan_networks()
        
        # 按信號強度排序（從強到弱）
        networks.sort(key=lambda x: x.get('signal', 0), reverse=True)
        
        formatted_networks = []
        for i, network in enumerate(networks, 1):
            formatted_network = {
                'id': i,
                'ssid': network.get('ssid', 'Unknown'),
                'signal_strength': network.get('signal', 0),
                'signal_bars': self._get_signal_bars(network.get('signal', 0)),
                'encrypted': network.get('encrypted', True),
                'security_type': network.get('auth_type', 'Unknown'),
                'bssid': network.get('bssid', ''),
                'description': self._get_network_description(network)
            }
            formatted_networks.append(formatted_network)
        
        return formatted_networks
    
    def _get_signal_bars(self, signal_strength):
        """根據信號強度返回信號條數（1-4）"""
        if signal_strength >= 75:
            return 4
        elif signal_strength >= 50:
            return 3
        elif signal_strength >= 25:
            return 2
        else:
            return 1
    
    def _get_network_description(self, network):
        """生成網路的描述文字"""
        ssid = network.get('ssid', 'Unknown')
        signal = network.get('signal', 0)
        encrypted = network.get('encrypted', True)
        auth_type = network.get('auth_type', '')
        
        security_text = "加密" if encrypted else "開放"
        if auth_type and encrypted:
            security_text = f"{auth_type}"
        
        return f"{ssid} - 信號: {signal}% - {security_text}"
    
    def _scan_windows(self):
        """Windows 系統的 WiFi 掃描"""
        networks = []
        try:
            # 首先檢查 WiFi 服務狀態
            self._check_wifi_service()
            
            # 檢查 WiFi 適配器狀態
            self._check_wifi_adapter()
            
            # 使用 netsh 命令掃描 WiFi
            result = subprocess.run(
                ['netsh', 'wlan', 'show', 'profile'],
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='ignore'  # 忽略無法解碼的字元
            )
            
            logger.info(f"netsh profile 命令返回碼: {result.returncode}")
            if result.stderr:
                logger.info(f"netsh profile 錯誤輸出: {result.stderr}")
            
            if result.returncode != 0:
                logger.error(f"netsh profile 命令失敗: {result.stderr}")
                # 嘗試直接掃描而不依賴已保存的配置文件
                return self._direct_scan_windows()
            
            # 檢查 stdout 是否為 None 或空
            if not result.stdout or not result.stdout.strip():
                logger.warning("netsh profile 命令輸出為空，可能沒有已保存的 WiFi 配置文件")
                # 直接進行網路掃描
                return self._direct_scan_windows()

            # 解析已儲存的網路設定檔
            saved_profiles = []
            for line in result.stdout.split('\n'):
                if '所有使用者設定檔' in line or 'All User Profile' in line:
                    # 提取網路名稱
                    match = re.search(r': (.+)$', line.strip())
                    if match:
                        saved_profiles.append(match.group(1).strip())
            
            logger.info(f"找到 {len(saved_profiles)} 個已保存的 WiFi 配置文件")
            
            # 掃描可用的網路
            scan_result = subprocess.run(
                ['netsh', 'wlan', 'show', 'interfaces'],
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='ignore'
            )
            
            # 直接進行網路掃描
            networks = self._direct_scan_windows()
            
        except Exception as e:
            logger.error(f"Windows WiFi 掃描錯誤: {e}")
            # 返回示例資料用於測試
            networks = [
                {
                    'ssid': 'WiFi網路1',
                    'signal': 80,
                    'encrypted': True,
                    'bssid': '00:11:22:33:44:55'
                },
                {
                    'ssid': '開放網路',
                    'signal': 65,
                    'encrypted': False,
                    'bssid': '00:11:22:33:44:56'
                }
            ]
        
        return networks
    
    def _parse_windows_scan(self, output):
        """解析 Windows netsh 掃描結果"""
        networks = []
        current_network = {}
        
        # 檢查輸出是否為 None 或空字符串
        if not output:
            logger.warning("Windows 掃描輸出為空")
            return networks
        
        logger.info(f"開始解析 netsh 輸出，共 {len(output.split(chr(10)))} 行")
        logger.debug(f"解析 netsh 輸出:\n{output}")
        
        lines = output.split('\n')
        for i, line in enumerate(lines):
            line = line.strip()
            
            # 匹配 SSID 行，但排除 BSSID 行
            # "SSID 1 : NetworkName" 但不是 "BSSID 1 : xx:xx:xx:xx:xx:xx"
            if re.search(r'^SSID\s+\d+\s*:', line, re.IGNORECASE) and not re.search(r'BSSID', line, re.IGNORECASE):
                # 如果已經有網路資料，先保存
                if current_network and 'ssid' in current_network:
                    networks.append(current_network.copy())
                    logger.debug(f"保存網路: {current_network}")
                    current_network = {}
                
                # 提取 SSID
                ssid_match = re.search(r'SSID\s+\d+\s*:\s*(.+)$', line, re.IGNORECASE)
                if ssid_match:
                    ssid = ssid_match.group(1).strip()
                    if ssid and ssid not in ['', '(null)', 'null', 'N/A']:
                        current_network['ssid'] = ssid
                        logger.info(f"找到 SSID: '{ssid}'")
            
            # 匹配網路類型行（通常在SSID後面）
            elif re.search(r'(網路類型|Network type)\s*:', line, re.IGNORECASE):
                network_type_match = re.search(r':\s*(.+)$', line)
                if network_type_match:
                    network_type = network_type_match.group(1).strip()
                    current_network['network_type'] = network_type
                    logger.debug(f"網路類型: {network_type}")
            
            # 匹配驗證類型
            elif re.search(r'(驗證|Authentication)\s*:', line, re.IGNORECASE):
                auth_match = re.search(r':\s*(.+)$', line)
                if auth_match:
                    auth_type = auth_match.group(1).strip()
                    # 判斷是否為開放網路
                    is_open = any(keyword in auth_type.lower() for keyword in ['open', '開放', 'none'])
                    current_network['encrypted'] = not is_open
                    current_network['auth_type'] = auth_type
                    logger.debug(f"驗證類型: {auth_type}, 加密: {not is_open}")
            
            # 匹配加密類型
            elif re.search(r'(加密|Encryption)\s*:', line, re.IGNORECASE):
                encryption_match = re.search(r':\s*(.+)$', line)
                if encryption_match:
                    encryption = encryption_match.group(1).strip()
                    current_network['encryption'] = encryption
                    # 如果還沒設定加密狀態，根據加密類型判斷
                    if 'encrypted' not in current_network:
                        is_encrypted = not any(keyword in encryption.lower() for keyword in ['none', '無', 'open'])
                        current_network['encrypted'] = is_encrypted
                    logger.debug(f"加密類型: {encryption}")
            
            # 匹配信號強度（注意可能有多個空格）
            elif re.search(r'(訊號|Signal)\s*:', line, re.IGNORECASE):
                signal_match = re.search(r'(\d+)%', line)
                if signal_match:
                    signal_strength = int(signal_match.group(1))
                    current_network['signal'] = signal_strength
                    logger.debug(f"信號強度: {signal_strength}%")
            
            # 匹配 BSSID（確保這是 BSSID 而不是 SSID）
            elif re.search(r'BSSID\s+\d+\s*:', line, re.IGNORECASE):
                bssid_match = re.search(r'BSSID\s+\d+\s*:\s*([a-fA-F0-9:]+)', line, re.IGNORECASE)
                if bssid_match:
                    bssid = bssid_match.group(1).strip()
                    current_network['bssid'] = bssid
                    logger.debug(f"BSSID: {bssid}")
        
        # 添加最後一個網路
        if current_network and 'ssid' in current_network:
            networks.append(current_network.copy())
            logger.debug(f"添加最後一個網路: {current_network}")
        
        # 確保所有網路都有必要的欄位
        for network in networks:
            if 'signal' not in network:
                network['signal'] = 50  # 預設值
            if 'encrypted' not in network:
                network['encrypted'] = True  # 預設為加密
            if 'bssid' not in network:
                network['bssid'] = '00:00:00:00:00:00'
        
        # 去除重複的網路（根據SSID）
        unique_networks = []
        seen_ssids = set()
        for network in networks:
            ssid = network.get('ssid', '')
            if ssid and ssid not in seen_ssids:
                unique_networks.append(network)
                seen_ssids.add(ssid)
        
        logger.info(f"解析完成，找到 {len(unique_networks)} 個唯一網路")
        return unique_networks
    
    def _scan_linux(self):
        """Linux 系統的 WiFi 掃描"""
        networks = []
        try:
            # 優先使用 nmcli（更現代的方法）
            result = subprocess.run(
                ['nmcli', '-f', 'SSID,SIGNAL,SECURITY,BSSID', 'dev', 'wifi', 'list'],
                capture_output=True,
                text=True,
                timeout=15
            )
            
            if result.returncode == 0 and result.stdout:
                networks = self._parse_nmcli_scan(result.stdout)
                logger.info(f"使用 nmcli 掃描到 {len(networks)} 個網路")
            else:
                logger.warning("nmcli 掃描失敗，嘗試使用 iwlist")
                # 備用方案：使用 iwlist 命令掃描
                result = subprocess.run(
                    ['sudo', 'iwlist', 'scan'],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                
                if result.returncode == 0 and result.stdout:
                    networks = self._parse_linux_scan(result.stdout)
                    logger.info(f"使用 iwlist 掃描到 {len(networks)} 個網路")
        
        except Exception as e:
            logger.error(f"Linux WiFi 掃描錯誤: {e}")
        
        return networks
    
    def _parse_linux_scan(self, output):
        """解析 Linux iwlist 掃描結果"""
        networks = []
        current_network = {}
        
        # 檢查輸出是否為 None 或空字符串
        if not output:
            logger.warning("Linux iwlist 掃描輸出為空")
            return networks
        
        logger.debug(f"開始解析 iwlist 輸出，共 {len(output.split(chr(10)))} 行")
        
        for line in output.split('\n'):
            line = line.strip()
            
            # 匹配新的網路區塊
            if 'Cell' in line and 'Address:' in line:
                # 保存之前的網路
                if current_network and 'ssid' in current_network:
                    networks.append(current_network.copy())
                    logger.debug(f"保存網路: {current_network}")
                current_network = {}
                
                # 提取 BSSID
                bssid_match = re.search(r'Address:\s*([a-fA-F0-9:]+)', line)
                if bssid_match:
                    current_network['bssid'] = bssid_match.group(1)
            
            # 匹配 SSID
            elif 'ESSID:' in line:
                ssid_match = re.search(r'ESSID:"(.+?)"', line)
                if ssid_match:
                    ssid = ssid_match.group(1)
                    if ssid and ssid not in ['', '\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00']:
                        current_network['ssid'] = ssid
                        logger.debug(f"找到 SSID: '{ssid}'")
            
            # 匹配信號品質
            elif 'Quality=' in line:
                quality_match = re.search(r'Quality=(\d+)/(\d+)', line)
                if quality_match:
                    quality = int(quality_match.group(1))
                    max_quality = int(quality_match.group(2))
                    signal = int((quality / max_quality) * 100)
                    current_network['signal'] = signal
                    logger.debug(f"信號強度: {signal}%")
                
                # 也可能包含信號級別
                signal_match = re.search(r'Signal level=([+-]?\d+)', line)
                if signal_match:
                    signal_dbm = int(signal_match.group(1))
                    # 轉換 dBm 到百分比 (簡化算法)
                    if signal_dbm >= -50:
                        signal_percent = 100
                    elif signal_dbm <= -100:
                        signal_percent = 0
                    else:
                        signal_percent = 2 * (signal_dbm + 100)
                    current_network['signal'] = max(current_network.get('signal', 0), signal_percent)
            
            # 匹配加密狀態
            elif 'Encryption key:' in line:
                current_network['encrypted'] = 'on' in line.lower()
                logger.debug(f"加密狀態: {current_network['encrypted']}")
            
            # 匹配 IE 信息（包含加密類型）
            elif 'IE:' in line and ('WPA' in line or 'RSN' in line):
                current_network['encrypted'] = True
                if 'WPA2' in line:
                    current_network['auth_type'] = 'WPA2'
                elif 'WPA' in line:
                    current_network['auth_type'] = 'WPA'
        
        # 添加最後一個網路
        if current_network and 'ssid' in current_network:
            networks.append(current_network.copy())
            logger.debug(f"添加最後一個網路: {current_network}")
        
        # 設置預設值
        for network in networks:
            if 'signal' not in network:
                network['signal'] = 50
            if 'encrypted' not in network:
                network['encrypted'] = True
            if 'bssid' not in network:
                network['bssid'] = '00:00:00:00:00:00'
        
        logger.info(f"iwlist 解析完成，找到 {len(networks)} 個網路")
        return networks
    
    def _parse_nmcli_scan(self, output):
        """解析 nmcli 掃描結果"""
        networks = []
        
        # 檢查輸出是否為 None 或空字符串
        if not output:
            logger.warning("nmcli 掃描輸出為空")
            return networks
        
        logger.debug(f"開始解析 nmcli 輸出，共 {len(output.split(chr(10)))} 行")
        logger.debug(f"nmcli 原始輸出:\n{output}")
        
        lines = output.split('\n')
        if len(lines) < 2:
            logger.warning("nmcli 輸出格式不正確，行數不足")
            return networks
        
        # 跳過標題行
        data_lines = lines[1:]
        
        for line_num, line in enumerate(data_lines, 2):
            line = line.strip()
            if not line:
                continue
            
            logger.debug(f"處理第 {line_num} 行: {repr(line)}")
            
            try:
                # nmcli 的輸出格式通常是用空白分隔的欄位
                # 格式: SSID SIGNAL BARS SECURITY
                parts = line.split()
                
                if len(parts) >= 2:
                    ssid = parts[0]
                    
                    # 跳過 BSSID 格式的行（包含冒號的 MAC 地址）
                    if ':' in ssid and len(ssid.split(':')) == 6:
                        logger.debug(f"跳過 BSSID 行: {ssid}")
                        continue
                    
                    # 跳過空的或無效的 SSID
                    if not ssid or ssid in ['--', '*', '']:
                        logger.debug(f"跳過無效 SSID: {repr(ssid)}")
                        continue
                    
                    # 解析信號強度
                    signal = 50  # 預設值
                    if len(parts) >= 2:
                        try:
                            # 第二個欄位通常是信號強度
                            signal_str = parts[1]
                            if signal_str.isdigit():
                                signal = int(signal_str)
                            elif signal_str.endswith('%'):
                                signal = int(signal_str[:-1])
                        except (ValueError, IndexError):
                            logger.debug(f"無法解析信號強度: {parts[1] if len(parts) > 1 else 'N/A'}")
                    
                    # 解析安全性設置
                    encrypted = True  # 預設為加密
                    security_type = "WPA"
                    
                    if len(parts) >= 4:
                        security = parts[3]
                        encrypted = security not in ['--', '', 'none', 'open']
                        if encrypted:
                            security_type = security
                    
                    network = {
                        'ssid': ssid,
                        'signal': signal,
                        'encrypted': encrypted,
                        'auth_type': security_type if encrypted else 'Open',
                        'bssid': '00:00:00:00:00:00'  # nmcli 基本命令不包含 BSSID
                    }
                    
                    networks.append(network)
                    logger.debug(f"添加網路: SSID='{ssid}', 信號={signal}%, 加密={encrypted}")
                
            except Exception as e:
                logger.error(f"解析第 {line_num} 行時發生錯誤: {e}, 行內容: {repr(line)}")
                continue
        
        # 去除重複的網路（根據 SSID）
        unique_networks = []
        seen_ssids = set()
        for network in networks:
            ssid = network.get('ssid', '')
            if ssid and ssid not in seen_ssids:
                unique_networks.append(network)
                seen_ssids.add(ssid)
        
        logger.info(f"nmcli 解析完成，找到 {len(unique_networks)} 個唯一網路")
        return unique_networks
    
    def connect_to_network(self, ssid, password=""):
        """連接到指定的 WiFi 網路"""
        try:
            if self.system == "Windows":
                return self._connect_windows(ssid, password)
            elif self.system == "Linux":
                return self._connect_linux(ssid, password)
            else:
                return False, f"不支援的作業系統: {self.system}"
        except Exception as e:
            logger.error(f"連接 WiFi 失敗: {e}")
            return False, str(e)
    
    def _connect_windows(self, ssid, password):
        """Windows 系統連接 WiFi"""
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
                
                # 寫入臨時檔案
                import tempfile
                with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False) as f:
                    f.write(profile_xml)
                    profile_path = f.name
                
                # 添加設定檔
                result = subprocess.run(
                    ['netsh', 'wlan', 'add', 'profile', f'filename={profile_path}'],
                    capture_output=True,
                    text=True,
                    encoding='utf-8',
                    errors='ignore'
                )
                
                # 清理臨時檔案
                import os
                os.unlink(profile_path)
                
                if result.returncode != 0:
                    return False, f"添加設定檔失敗: {result.stderr}"
            
            # 連接到網路
            result = subprocess.run(
                ['netsh', 'wlan', 'connect', f'name={ssid}'],
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='ignore'
            )
            
            if result.returncode == 0:
                return True, "連接成功"
            else:
                return False, f"連接失敗: {result.stderr}"
                
        except Exception as e:
            return False, f"Windows 連接錯誤: {e}"
    
    def _connect_linux(self, ssid, password):
        """Linux 系統連接 WiFi"""
        try:
            if password:
                result = subprocess.run(
                    ['nmcli', 'dev', 'wifi', 'connect', ssid, 'password', password],
                    capture_output=True,
                    text=True
                )
            else:
                result = subprocess.run(
                    ['nmcli', 'dev', 'wifi', 'connect', ssid],
                    capture_output=True,
                    text=True
                )
            
            if result.returncode == 0:
                return True, "連接成功"
            else:
                return False, f"連接失敗: {result.stderr}"
                
        except Exception as e:
            return False, f"Linux 連接錯誤: {e}"
    
    def get_current_connection(self):
        """獲取當前的 WiFi 連接狀態"""
        try:
            if self.system == "Windows":
                return self._get_windows_connection()
            elif self.system == "Linux":
                return self._get_linux_connection()
            else:
                return None
        except Exception as e:
            logger.error(f"獲取連接狀態失敗: {e}")
            return None
    
    def _get_windows_connection(self):
        """獲取 Windows 當前 WiFi 連接"""
        try:
            result = subprocess.run(
                ['netsh', 'wlan', 'show', 'interfaces'],
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='ignore'
            )
            stdout = result.stdout or ""
            
            if result.returncode == 0:
                for line in stdout.split('\n'):
                    if 'SSID' in line and ':' in line:
                        ssid = line.split(':', 1)[1].strip()
                        if ssid:
                            return {
                                'connected': True,
                                'ssid': ssid,
                                'ip': self._get_ip_address(),
                                'signal': 'N/A'
                            }
            
            return {
                'connected': False,
                'ssid': None,
                'ip': None,
                'signal': None
            }
            
        except Exception as e:
            logger.error(f"獲取 Windows 連接狀態錯誤: {e}")
            return None
    
    def _get_linux_connection(self):
        """獲取 Linux 當前 WiFi 連接"""
        try:
            result = subprocess.run(
                ['nmcli', '-t', '-f', 'ACTIVE,SSID', 'dev', 'wifi'],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0 and result.stdout:
                for line in result.stdout.split('\n'):
                    if line.startswith('yes:'):
                        ssid = line.split(':', 1)[1]
                        return {
                            'connected': True,
                            'ssid': ssid,
                            'ip': self._get_ip_address(),
                            'signal': 'N/A'
                        }
            
            return {
                'connected': False,
                'ssid': None,
                'ip': None,
                'signal': None
            }
            
        except Exception as e:
            logger.error(f"獲取 Linux 連接狀態錯誤: {e}")
            return None
    
    def _get_ip_address(self):
        """獲取 IP 地址"""
        try:
            if self.system == "Windows":
                result = subprocess.run(
                    ['ipconfig'],
                    capture_output=True,
                    text=True,
                    encoding='utf-8',
                    errors='ignore'
                )
                stdout = result.stdout or ""
                for line in stdout.split('\n'):
                    if 'IPv4' in line and '192.' in line:
                        ip_match = re.search(r'(\d+\.\d+\.\d+\.\d+)', line)
                        if ip_match:
                            return ip_match.group(1)
            elif self.system == "Linux":
                result = subprocess.run(
                    ['hostname', '-I'],
                    capture_output=True,
                    text=True
                )
                stdout = result.stdout or ""
                if result.returncode == 0:
                    ips = stdout.strip().split()
                    for ip in ips:
                        # 只返回私有網段 IP
                        if ip.startswith('192.') or ip.startswith('10.') or ip.startswith('172.'):
                            return ip
        except Exception as e:
            logger.error(f"獲取 IP 地址錯誤: {e}")
        return None
    
    def _check_wifi_service(self):
        """檢查 Windows WiFi 服務狀態"""
        try:
            result = subprocess.run(
                ['sc', 'query', 'wlansvc'],
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='ignore'
            )
            
            if result.returncode == 0:
                if 'RUNNING' in result.stdout:
                    logger.info("WiFi 服務正在運行")
                else:
                    logger.warning("WiFi 服務未運行")
                    # 嘗試啟動服務
                    subprocess.run(['sc', 'start', 'wlansvc'], capture_output=True)
            else:
                logger.warning("無法查詢 WiFi 服務狀態")
        except Exception as e:
            logger.error(f"檢查 WiFi 服務錯誤: {e}")
    
    def _check_wifi_adapter(self):
        """檢查 WiFi 適配器狀態"""
        try:
            result = subprocess.run(
                ['netsh', 'wlan', 'show', 'drivers'],
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='ignore'
            )
            
            if result.returncode == 0:
                if result.stdout and ('Driver' in result.stdout or '驅動程式' in result.stdout or 'Wireless LAN adapter' in result.stdout):
                    logger.info("WiFi 適配器驅動程式已安裝")
                else:
                    logger.info("WiFi 適配器狀態檢查完成")
            else:
                logger.warning("無法查詢 WiFi 適配器狀態")
        except Exception as e:
            logger.error(f"檢查 WiFi 適配器錯誤: {e}")
    
    def _direct_scan_windows(self):
        """直接掃描 Windows WiFi 網路（不依賴已保存的配置文件）"""
        networks = []
        try:
            # 執行網路掃描，不使用 refresh 命令以避免問題
            scan_cmd = ['netsh', 'wlan', 'show', 'networks', 'mode=bssid']
            logger.info(f"執行掃描命令: {' '.join(scan_cmd)}")
            
            scan_result = subprocess.run(
                scan_cmd,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='ignore',
                timeout=15
            )
            
            logger.info(f"掃描命令返回碼: {scan_result.returncode}")
            
            if scan_result.returncode == 0:
                if scan_result.stdout and scan_result.stdout.strip():
                    logger.info(f"掃描輸出長度: {len(scan_result.stdout)} 字符")
                    
                    # 輸出原始掃描結果進行調試
                    logger.info("=== 原始掃描輸出開始 ===")
                    lines = scan_result.stdout.split('\n')
                    for i, line in enumerate(lines, 1):
                        logger.info(f"{i:3d}: {repr(line)}")
                    logger.info("=== 原始掃描輸出結束 ===")
                    
                    # 解析掃描結果
                    networks = self._parse_windows_scan(scan_result.stdout)
                    
                    if networks:
                        logger.info(f"成功解析到 {len(networks)} 個網路:")
                        for i, network in enumerate(networks, 1):
                            logger.info(f"  {i}. SSID: '{network.get('ssid', 'N/A')}', "
                                      f"信號: {network.get('signal', 'N/A')}%, "
                                      f"加密: {network.get('encrypted', 'N/A')}")
                    else:
                        logger.warning("掃描成功但沒有解析到任何網路")
                        # 嘗試使用簡化的解析方法
                        networks = self._simple_parse_windows_scan(scan_result.stdout)
                else:
                    logger.warning("掃描命令成功但輸出為空")
            else:
                logger.error(f"掃描命令失敗，返回碼: {scan_result.returncode}")
                if scan_result.stderr:
                    logger.error(f"錯誤信息: {scan_result.stderr}")
                
        except subprocess.TimeoutExpired:
            logger.error("掃描命令超時")
        except Exception as e:
            logger.error(f"直接掃描錯誤: {e}")
            
        return networks
    
    def _simple_parse_windows_scan(self, output):
        """簡化的 Windows 掃描結果解析"""
        networks = []
        lines = output.split('\n')
        
        logger.info("使用簡化解析方法")
        
        # 查找包含 SSID 的行
        for line in lines:
            line = line.strip()
            # 更寬鬆的 SSID 匹配
            if 'SSID' in line and ':' in line:
                # 提取冒號後的內容
                parts = line.split(':', 1)
                if len(parts) == 2:
                    ssid = parts[1].strip()
                    if ssid and ssid not in ['', '(null)', 'null', 'N/A']:
                        networks.append({
                            'ssid': ssid,
                            'signal': 50,  # 預設信號強度
                            'encrypted': True,  # 預設為加密
                            'bssid': '00:00:00:00:00:00'
                        })
                        logger.info(f"簡化解析找到網路: {ssid}")
        
        return networks

# 全域 WiFi 管理器實例，供其他模組使用
wifi_manager = WiFiManager()

# 如果直接運行此檔案，執行測試
if __name__ == "__main__":
    # 設置日誌級別為 INFO 以查看詳細信息
    logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(name)s:%(message)s')
    
    print("測試 WiFi 掃描功能...")
    networks = wifi_manager.scan_networks()
    
    print(f"\n找到 {len(networks)} 個網路:")
    for i, network in enumerate(networks, 1):
        print(f"  {i}. SSID: {network.get('ssid', 'N/A')}")
        print(f"     信號: {network.get('signal', 'N/A')}%")
        print(f"     加密: {'是' if network.get('encrypted', True) else '否'}")
        print(f"     BSSID: {network.get('bssid', 'N/A')}")
    
    print("\n測試格式化網路列表...")
    formatted_networks = wifi_manager.get_available_networks()
    
    print(f"\n可用網路列表:")
    print("=" * 50)
    for network in formatted_networks:
        bars = "●" * network['signal_bars'] + "○" * (4 - network['signal_bars'])
        security = "🔒" if network['encrypted'] else "🔓"
        print(f"{network['id']:2d}. {security} {network['ssid']}")
        print(f"    信號: {bars} ({network['signal_strength']}%)")
        if network['encrypted']:
            print(f"    安全: {network['security_type']}")
        print()
    
    print("測試完成")
