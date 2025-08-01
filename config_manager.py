#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置管理模組
提供統一的配置檔案管理和協定配置
"""

import json
import os
import logging
from typing import Dict, Any, List, Optional
from utils.config_validator import validate_and_fix_config

class ConfigManager:
    """配置管理器"""
    
    def __init__(self, config_file: str = "config.json"):
        """
        初始化配置管理器
        
        Args:
            config_file: 配置檔案路徑
        """
        self.config_file = config_file
        self.config = {}
        self.logger = logging.getLogger(__name__)
        
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置管理模組
提供統一的配置檔案管理和協定配置
"""

import json
import os
import logging
from typing import Dict, Any, List, Optional, Tuple
from utils.config_validator import validate_and_fix_config

class ConfigManager:
    """
    配置管理器
    提供配置檔案的載入、儲存、驗證和管理功能
    """
    
    def __init__(self, config_file: str = "config.json"):
        """
        初始化配置管理器
        
        Args:
            config_file: 配置檔案路徑
        """
        self.config_file = config_file
        self.config = {}
        self.logger = logging.getLogger(__name__)
        
        # 載入並驗證配置
        self._load_and_validate_config()
    
    def _get_default_serial_port(self, protocol_type: str) -> str:
        """
        根據作業系統和協定類型獲取預設串口
        
        Args:
            protocol_type: 協定類型 (UART, RTU)
            
        Returns:
            str: 預設串口名稱
        """
        if os.name == 'nt':  # Windows
            return "COM6" if protocol_type == "UART" else "COM4"
        else:  # Linux/Unix
            return "/dev/ttyUSB0" if protocol_type == "UART" else "/dev/ttyUSB1"
    
    def _load_and_validate_config(self):
        """載入並驗證配置檔案"""
        try:
            # 使用配置驗證器載入和驗證配置
            success, config, messages = validate_and_fix_config(self.config_file, auto_fix=True)
            
            if success:
                self.config = config
                self.logger.info("配置檔案載入成功")
                for message in messages:
                    self.logger.info(message)
            else:
                self.logger.error("配置檔案驗證失敗")
                for message in messages:
                    self.logger.error(message)
                
                # 使用預設配置
                self.config = self._get_default_config()
                self.save_config()
                
        except Exception as e:
            self.logger.error(f"載入配置檔案時發生錯誤: {e}")
            self.config = self._get_default_config()
            self.save_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """
        獲取預設配置
        
        Returns:
            Dict[str, Any]: 預設配置字典
        """
        return {
            "protocols": {
                "UART": {
                    "com_port": self._get_default_serial_port("UART"),
                    "baud_rate": 9600,
                    "parity": "N",
                    "stopbits": 1,
                    "bytesize": 8,
                    "timeout": 1
                },
                "MQTT": {
                    "broker": "localhost",
                    "port": 1883,
                    "topic": "ct_data",
                    "username": "",
                    "password": "",
                    "keepalive": 60,
                    "qos": 0
                },
                "RTU": {
                    "com_port": self._get_default_serial_port("RTU"),
                    "baud_rate": 9600,
                    "parity": "N",
                    "stopbits": 1,
                    "bytesize": 8,
                    "timeout": 1
                },
                "FTP": {
                    "host": "192.168.1.100",
                    "port": 21,
                    "username": "ftp_user",
                    "password": "ftp_password",
                    "remote_dir": "/uploads/",
                    "passive_mode": True
                },
                "FastAPI": {
                    "host": "localhost",
                    "port": 8000,
                    "endpoint": "/upload",
                    "timeout": 30
                },
                "TCP": {
                    "host": "0.0.0.0",
                    "port": 5020,
                    "timeout": 10,
                    "retry_count": 3
                }
            },
            "offline_mode": True,
            "data_retention_days": 30,
            "max_data_points": 1000
        }
    
    def load_config(self) -> bool:
        """
        載入配置檔案
        
        Returns:
            bool: 是否成功載入
        """
        try:
            self._load_and_validate_config()
            self.logger.info("配置檔案載入成功")
            return True
        except Exception as e:
            self.logger.error(f"載入配置檔案失敗: {e}")
            return False
    
    def reload_config(self) -> bool:
        """
        重新載入配置檔案
        
        Returns:
            bool: 是否成功重新載入
        """
        try:
            self._load_and_validate_config()
            self.logger.info("配置檔案重新載入成功")
            return True
        except Exception as e:
            self.logger.error(f"重新載入配置檔案失敗: {e}")
            return False
    
    def save_config(self) -> bool:
        """
        儲存配置到檔案
        
        Returns:
            bool: 是否成功儲存
        """
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
            self.logger.info(f"配置已儲存到 {self.config_file}")
            return True
        except Exception as e:
            self.logger.error(f"儲存配置檔案時發生錯誤: {e}")
            return False
    
    # 一般配置方法
    def get(self, key: str, default: Any = None) -> Any:
        """
        獲取配置值
        
        Args:
            key: 配置鍵名
            default: 預設值
            
        Returns:
            Any: 配置值
        """
        return self.config.get(key, default)
    
    def set(self, key: str, value: Any) -> bool:
        """
        設定配置值
        
        Args:
            key: 配置鍵名
            value: 配置值
            
        Returns:
            bool: 是否成功設定
        """
        self.config[key] = value
        return self.save_config()
    
    def get_all(self) -> Dict[str, Any]:
        """
        獲取所有配置
        
        Returns:
            Dict[str, Any]: 所有配置的副本
        """
        return self.config.copy()
    
    # 協定配置方法
    def get_supported_protocols(self) -> List[str]:
        """
        獲取支援的協定列表
        
        Returns:
            List[str]: 支援的協定列表
        """
        protocols = self.config.get("protocols", {})
        return list(protocols.keys())
    
    def validate_protocol(self, protocol: str) -> bool:
        """
        驗證協定是否支援
        
        Args:
            protocol: 協定名稱
            
        Returns:
            bool: 是否支援該協定
        """
        protocols = self.config.get("protocols", {})
        return protocol in protocols
    
    def get_protocol_config(self, protocol: str) -> Dict[str, Any]:
        """
        獲取指定協定的配置
        
        Args:
            protocol: 協定名稱
            
        Returns:
            Dict[str, Any]: 協定配置的副本
        """
        protocols = self.config.get("protocols", {})
        return protocols.get(protocol, {}).copy()
    
    def update_protocol_config(self, protocol: str, config: Dict[str, Any]) -> bool:
        """
        更新指定協定的配置
        
        Args:
            protocol: 協定名稱
            config: 新的配置
            
        Returns:
            bool: 是否成功更新
        """
        if "protocols" not in self.config:
            self.config["protocols"] = {}
        
        if protocol not in self.config["protocols"]:
            self.logger.warning(f"協定 {protocol} 不存在，將創建新的配置")
        
        self.config["protocols"][protocol] = config
        
        # 設定配置標記，表示此協定已被用戶設定過
        self.config["protocols"][protocol]["configured"] = True
        
        return self.save_config()
    
    def get_protocol_field_info(self, protocol: str) -> Dict[str, Dict[str, Any]]:
        """
        獲取協定欄位的詳細資訊，用於生成表單
        
        Args:
            protocol: 協定名稱
            
        Returns:
            Dict[str, Dict[str, Any]]: 欄位資訊字典
        """
        field_info = {
            'MQTT': {
                'broker': {'type': 'text', 'label': 'MQTT Broker', 'required': True, 'placeholder': 'localhost'},
                'port': {'type': 'number', 'label': 'Port', 'required': True, 'min': 1, 'max': 65535, 'default': 1883},
                'topic': {'type': 'text', 'label': 'Topic', 'required': True, 'placeholder': 'ct_data'},
                'username': {'type': 'text', 'label': 'Username', 'required': False, 'placeholder': '使用者名稱'},
                'password': {'type': 'password', 'label': 'Password', 'required': False, 'placeholder': '密碼'},
                'keepalive': {'type': 'number', 'label': 'Keep Alive (秒)', 'required': False, 'min': 10, 'max': 3600, 'default': 60},
                'qos': {'type': 'select', 'label': 'QoS', 'required': False, 'options': [0, 1, 2], 'default': 0}
            },
            'RTU': {
                'com_port': {'type': 'text', 'label': 'COM 埠', 'required': True, 'placeholder': self._get_default_serial_port('RTU')},
                'baud_rate': {'type': 'select', 'label': '鮑率', 'required': True, 'options': [1200, 2400, 4800, 9600, 19200, 38400, 57600, 115200], 'default': 9600},
                'parity': {'type': 'select', 'label': '同位元', 'required': True, 'options': ['N', 'E', 'O', 'M', 'S'], 'default': 'N'},
                'stopbits': {'type': 'select', 'label': '停止位元', 'required': True, 'options': [1, 1.5, 2], 'default': 1},
                'bytesize': {'type': 'select', 'label': '資料位元', 'required': True, 'options': [5, 6, 7, 8], 'default': 8},
                'timeout': {'type': 'number', 'label': '逾時(秒)', 'required': True, 'min': 0.1, 'max': 60, 'default': 1}
            },
            'FastAPI': {
                'host': {'type': 'text', 'label': 'API 主機', 'required': True, 'placeholder': 'localhost'},
                'port': {'type': 'number', 'label': 'Port', 'required': True, 'min': 1, 'max': 65535, 'default': 8000},
                'endpoint': {'type': 'text', 'label': '端點', 'required': True, 'placeholder': '/upload'},
                'timeout': {'type': 'number', 'label': '逾時 (秒)', 'required': False, 'min': 1, 'max': 300, 'default': 30}
            },
            'TCP': {
                'host': {'type': 'text', 'label': 'TCP 主機', 'required': True, 'placeholder': '0.0.0.0'},
                'port': {'type': 'number', 'label': 'Port', 'required': True, 'min': 1, 'max': 65535, 'default': 5020},
                'timeout': {'type': 'number', 'label': '逾時 (秒)', 'required': False, 'min': 1, 'max': 60, 'default': 10},
                'retry_count': {'type': 'number', 'label': '重試次數', 'required': False, 'min': 0, 'max': 10, 'default': 3}
            },
            'UART': {
                'com_port': {'type': 'text', 'label': 'COM 埠', 'required': True, 'placeholder': self._get_default_serial_port('UART')},
                'baud_rate': {'type': 'select', 'label': '鮑率', 'required': True, 'options': [1200, 2400, 4800, 9600, 19200, 38400, 57600, 115200], 'default': 9600},
                'parity': {'type': 'select', 'label': '同位元', 'required': True, 'options': ['N', 'E', 'O', 'M', 'S'], 'default': 'N'},
                'stopbits': {'type': 'select', 'label': '停止位元', 'required': True, 'options': [1, 1.5, 2], 'default': 1},
                'bytesize': {'type': 'select', 'label': '資料位元', 'required': True, 'options': [5, 6, 7, 8], 'default': 8},
                'timeout': {'type': 'number', 'label': '逾時(秒)', 'required': True, 'min': 0.1, 'max': 60, 'default': 1}
            },
            'FTP': {
                'host': {'type': 'text', 'label': 'FTP 主機', 'required': True, 'placeholder': '192.168.1.100'},
                'port': {'type': 'number', 'label': 'Port', 'required': True, 'min': 1, 'max': 65535, 'default': 21},
                'username': {'type': 'text', 'label': '使用者名稱', 'required': True, 'placeholder': 'ftp_user'},
                'password': {'type': 'password', 'label': '密碼', 'required': True, 'placeholder': 'ftp_password'},
                'remote_dir': {'type': 'text', 'label': '遠端目錄', 'required': True, 'placeholder': '/uploads/'},
                'passive_mode': {'type': 'checkbox', 'label': '被動模式', 'required': False, 'default': True}
            }
        }
        return field_info.get(protocol, {})
    
    def validate_protocol_config(self, protocol: str, config: Dict[str, Any]) -> Tuple[bool, Dict[str, List[str]]]:
        """
        驗證協定配置值
        
        Args:
            protocol: 協定名稱
            config: 要驗證的配置
            
        Returns:
            Tuple[bool, Dict[str, List[str]]]: (是否有效, 錯誤訊息字典)
        """
        errors = {}
        field_info = self.get_protocol_field_info(protocol)
        
        for field, value in config.items():
            if field not in field_info:
                continue
                
            field_config = field_info[field]
            field_errors = []
            
            # 檢查必填欄位
            if field_config.get('required', False) and (value is None or value == ""):
                field_errors.append('此欄位為必填')
            
            # 檢查數值範圍
            if field_config['type'] in ['number', 'select'] and value is not None:
                try:
                    numeric_value = float(value)
                    
                    if 'min' in field_config and numeric_value < field_config['min']:
                        field_errors.append(f'最小值為 {field_config["min"]}')
                    
                    if 'max' in field_config and numeric_value > field_config['max']:
                        field_errors.append(f'最大值為 {field_config["max"]}')
                    
                    # 檢查選項值
                    if 'options' in field_config and numeric_value not in field_config['options']:
                        field_errors.append(f'請選擇有效選項: {field_config["options"]}')
                        
                except (ValueError, TypeError):
                    field_errors.append('請輸入有效的數值')
            
            # 檢查選項值（非數值）
            if field_config.get('type') == 'select' and 'options' in field_config:
                if value not in field_config['options']:
                    field_errors.append(f'請選擇有效選項: {field_config["options"]}')
            
            if field_errors:
                errors[field] = field_errors
        
        return len(errors) == 0, errors
    
    def get_protocol_description(self, protocol: str) -> str:
        """
        獲取協定描述
        
        Args:
            protocol: 協定名稱
            
        Returns:
            str: 協定描述
        """
        descriptions = {
            'MQTT': '輕量級訊息傳輸協定，適用於IoT設備和即時資料傳輸',
            'RTU': 'Modbus RTU協定，適用於串列通訊和工業設備',
            'FastAPI': '現代化API框架，適用於RESTful API和微服務',
            'TCP': 'Modbus TCP協定，適用於網路通訊和遠端控制',
            'UART': '通用非同步收發傳輸器，適用於串列通訊和設備資料讀取',
            'FTP': '檔案傳輸協定，適用於檔案上傳和備份'
        }
        return descriptions.get(protocol, '未知協定')
    
    # 匯出入功能
    def export_config(self, filepath: str) -> bool:
        """
        匯出配置到指定檔案
        
        Args:
            filepath: 匯出檔案路徑
            
        Returns:
            bool: 是否成功匯出
        """
        try:
            export_data = {
                'version': '1.0',
                'export_time': str(logging.Formatter().formatTime(logging.LogRecord('', 0, '', 0, '', (), None))),
                'config': self.config
            }
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"配置已匯出到 {filepath}")
            return True
        except Exception as e:
            self.logger.error(f"匯出配置時發生錯誤: {e}")
            return False
    
    def import_config(self, filepath: str) -> bool:
        """
        從指定檔案匯入配置
        
        Args:
            filepath: 匯入檔案路徑
            
        Returns:
            bool: 是否成功匯入
        """
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                import_data = json.load(f)
            
            # 檢查匯入資料格式
            if 'config' in import_data:
                self.config = import_data['config']
            else:
                # 相容舊格式
                self.config = import_data
            
            # 驗證匯入的配置
            success, config, messages = validate_and_fix_config(self.config_file, auto_fix=True)
            
            if success:
                self.save_config()
                self.logger.info(f"配置已從 {filepath} 匯入")
                return True
            else:
                self.logger.error("匯入的配置檔案格式不正確")
                return False
                
        except Exception as e:
            self.logger.error(f"匯入配置時發生錯誤: {e}")
            return False
    
    # 設定備份和還原
    def backup_config(self, backup_dir: str = "backups") -> Optional[str]:
        """
        備份目前配置
        
        Args:
            backup_dir: 備份目錄
            
        Returns:
            Optional[str]: 備份檔案路徑，失敗時返回 None
        """
        try:
            import datetime
            
            # 建立備份目錄
            os.makedirs(backup_dir, exist_ok=True)
            
            # 生成備份檔案名稱
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_filename = f"config_backup_{timestamp}.json"
            backup_path = os.path.join(backup_dir, backup_filename)
            
            # 匯出配置到備份檔案
            if self.export_config(backup_path):
                self.logger.info(f"配置已備份到 {backup_path}")
                return backup_path
            else:
                return None
                
        except Exception as e:
            self.logger.error(f"備份配置時發生錯誤: {e}")
            return None
    
    def list_backups(self, backup_dir: str = "backups") -> List[str]:
        """
        列出所有備份檔案
        
        Args:
            backup_dir: 備份目錄
            
        Returns:
            List[str]: 備份檔案列表
        """
        try:
            if not os.path.exists(backup_dir):
                return []
            
            backup_files = []
            for filename in os.listdir(backup_dir):
                if filename.startswith("config_backup_") and filename.endswith(".json"):
                    backup_files.append(os.path.join(backup_dir, filename))
            
            # 按修改時間排序（最新的在前）
            backup_files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
            return backup_files
            
        except Exception as e:
            self.logger.error(f"列出備份檔案時發生錯誤: {e}")
            return []
    
    def restore_config(self, backup_path: str) -> bool:
        """
        從備份還原配置
        
        Args:
            backup_path: 備份檔案路徑
            
        Returns:
            bool: 是否成功還原
        """
        try:
            # 先備份目前配置
            current_backup = self.backup_config()
            if current_backup:
                self.logger.info(f"目前配置已備份到 {current_backup}")
            
            # 匯入備份配置
            if self.import_config(backup_path):
                self.logger.info(f"配置已從備份 {backup_path} 還原")
                return True
            else:
                return False
                
        except Exception as e:
            self.logger.error(f"還原配置時發生錯誤: {e}")
            return False
    
    def get_active_protocol(self) -> str:
        """
        取得目前啟用的通訊協定
        
        Returns:
            str: 目前啟用的協定名稱
        """
        active = self.config.get('active_protocol', 'None')
        
        # 如果有明確設定的協定且該協定已配置，直接回傳
        if active and active != 'None' and self.is_protocol_configured(active):
            return active
            
        # 尋找第一個已設定的協定（排除 UART）
        for protocol in self.get_supported_protocols():
            if protocol != 'UART' and self.is_protocol_configured(protocol):
                self.logger.info(f"自動選擇已設定的協定: {protocol}")
                # 自動設定為啟用協定
                self.config['active_protocol'] = protocol
                self.save_config()
                return protocol
            
        # 最後才回傳 UART 作為預設值
        return 'UART'
    
    def set_active_protocol(self, protocol: str) -> bool:
        """
        設定目前啟用的通訊協定
        
        Args:
            protocol: 要設定為啟用的協定名稱
            
        Returns:
            bool: 設定是否成功
        """
        if self.validate_protocol(protocol):
            old_active = self.config.get('active_protocol', 'None')
            self.config['active_protocol'] = protocol
            if self.save_config():
                self.logger.info(f"已設定啟用協定從 {old_active} 變更為: {protocol}")
                return True
            else:
                self.logger.error(f"設定啟用協定失敗: {protocol} (儲存配置失敗)")
                return False
        else:
            self.logger.error(f"無效的協定名稱: {protocol}")
            return False
    
    def is_protocol_configured(self, protocol: str) -> bool:
        """
        檢查協定是否已實際設定（有使用者自訂配置）
        
        Args:
            protocol: 協定名稱
            
        Returns:
            bool: 協定是否已設定
        """
        if not self.validate_protocol(protocol):
            return False
            
        # 檢查協定配置中的設定標記
        config = self.get_protocol_config(protocol)
        return config.get('configured', False)
    
    def _get_protocol_defaults(self, protocol: str) -> Dict[str, Any]:
        """
        取得協定的預設配置
        
        Args:
            protocol: 協定名稱
            
        Returns:
            Dict[str, Any]: 預設配置
        """
        defaults = {
            "UART": {
                "com_port": "COM3",
                "baud_rate": 9600,
                "parity": "N",
                "stopbits": 1,
                "bytesize": 8,
                "timeout": 1
            },
            "MQTT": {
                "broker": "localhost",
                "port": 1883,
                "topic": "ct_data",
                "username": "",
                "password": "",
                "keepalive": 60,
                "qos": 0
            },
            "RTU": {
                "com_port": "COM4",
                "baud_rate": 9600,
                "parity": "N",
                "stopbits": 1,
                "bytesize": 8,
                "timeout": 1
            },
            "FTP": {
                "host": "192.168.1.100",
                "port": 21,
                "username": "ftp_user",
                "password": "ftp_password",
                "remote_dir": "/uploads/",
                "passive_mode": True
            },
            "FastAPI": {
                "host": "localhost",
                "port": 8000,
                "endpoint": "/upload",
                "timeout": 30
            },
            "TCP": {
                "host": "0.0.0.0",
                "port": 5020,
                "timeout": 10,
                "retry_count": 3
            }
        }
        return defaults.get(protocol, {})


# 全域配置管理器實例
_config_manager = None

def get_config_manager(config_file: str = "config.json") -> ConfigManager:
    """
    獲取全域配置管理器實例
    
    Args:
        config_file: 配置檔案路徑
        
    Returns:
        ConfigManager: 配置管理器實例
    """
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager(config_file)
    return _config_manager


if __name__ == "__main__":
    # 測試配置管理器
    import logging
    logging.basicConfig(level=logging.INFO)
    
    # 測試配置管理器
    config_manager = ConfigManager("test_config.json")
    
    # 測試基本功能
    print("支援的協定:", config_manager.get_supported_protocols())
    print("UART 配置:", config_manager.get_protocol_config("UART"))
    
    # 測試配置驗證
    uart_config = {"com_port": "COM3", "baud_rate": 9600}
    is_valid, errors = config_manager.validate_protocol_config("UART", uart_config)
    print(f"配置驗證結果: {is_valid}, 錯誤: {errors}")
    
    # 測試備份功能
    backup_path = config_manager.backup_config()
    if backup_path:
        print(f"配置已備份到: {backup_path}")
    
    print("測試完成！") 