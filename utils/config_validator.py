#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置驗證模組
提供配置檔案的驗證和錯誤檢查功能
"""

import os
import json
from typing import Dict, Any, List, Tuple, Optional
import logging

# 嘗試導入 jsonschema，如果沒有安裝則使用基本驗證
try:
    import jsonschema
    from jsonschema import validate, ValidationError
    JSONSCHEMA_AVAILABLE = True
except ImportError:
    JSONSCHEMA_AVAILABLE = False


class ConfigValidator:
    """配置驗證器"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # 定義配置 schema
        self.config_schema = {
            "type": "object",
            "properties": {
                "protocols": {
                    "type": "object",
                    "properties": {
                        "UART": {
                            "type": "object",
                            "properties": {
                                "com_port": {"type": "string"},
                                "baud_rate": {"type": "integer", "minimum": 1200, "maximum": 115200},
                                "parity": {"type": "string", "enum": ["N", "E", "O", "M", "S"]},
                                "stopbits": {"type": "number", "enum": [1, 1.5, 2]},
                                "bytesize": {"type": "integer", "enum": [5, 6, 7, 8]},
                                "timeout": {"type": "number", "minimum": 0.1, "maximum": 60},
                                "configured": {"type": "boolean"}
                            },
                            "required": ["com_port", "baud_rate"],
                            "additionalProperties": True
                        },
                        "MQTT": {
                            "type": "object",
                            "properties": {
                                "broker": {"type": "string"},
                                "port": {"type": "integer", "minimum": 1, "maximum": 65535},
                                "topic": {"type": "string"},
                                "username": {"type": "string"},
                                "password": {"type": "string"},
                                "keepalive": {"type": "integer", "minimum": 10, "maximum": 3600},
                                "qos": {"type": "integer", "enum": [0, 1, 2]},
                                "configured": {"type": "boolean"}
                            },
                            "required": ["broker", "port", "topic"],
                            "additionalProperties": True
                        },
                        "RTU": {
                            "type": "object",
                            "properties": {
                                "com_port": {"type": "string"},
                                "baud_rate": {"type": "integer", "minimum": 1200, "maximum": 115200},
                                "parity": {"type": "string", "enum": ["N", "E", "O", "M", "S"]},
                                "stopbits": {"type": "number", "enum": [1, 1.5, 2]},
                                "bytesize": {"type": "integer", "enum": [5, 6, 7, 8]},
                                "timeout": {"type": "number", "minimum": 0.1, "maximum": 60},
                                "configured": {"type": "boolean"}
                            },
                            "required": ["com_port", "baud_rate"],
                            "additionalProperties": True
                        },
                        "FTP": {
                            "type": "object",
                            "properties": {
                                "host": {"type": "string"},
                                "port": {"type": "integer", "minimum": 1, "maximum": 65535},
                                "username": {"type": "string"},
                                "password": {"type": "string"},
                                "remote_dir": {"type": "string"},
                                "passive_mode": {"type": "boolean"},
                                "configured": {"type": "boolean"}
                            },
                            "required": ["host", "username", "password"],
                            "additionalProperties": True
                        },
                        "FastAPI": {
                            "type": "object",
                            "properties": {
                                "host": {"type": "string"},
                                "port": {"type": "integer", "minimum": 1, "maximum": 65535},
                                "endpoint": {"type": "string"},
                                "timeout": {"type": "number", "minimum": 1, "maximum": 300},
                                "configured": {"type": "boolean"}
                            },
                            "required": ["host", "port", "endpoint"],
                            "additionalProperties": True
                        },
                        "TCP": {
                            "type": "object",
                            "properties": {
                                "host": {"type": "string"},
                                "port": {"type": "integer", "minimum": 1, "maximum": 65535},
                                "timeout": {"type": "number", "minimum": 1, "maximum": 60},
                                "retry_count": {"type": "integer", "minimum": 1, "maximum": 10},
                                "configured": {"type": "boolean"}
                            },
                            "required": ["host", "port"],
                            "additionalProperties": True
                        }
                    },
                    "additionalProperties": True
                },
                "offline_mode": {"type": "boolean"},
                "data_retention_days": {"type": "integer", "minimum": 1, "maximum": 365},
                "max_data_points": {"type": "integer", "minimum": 100, "maximum": 10000}
            },
            "required": ["protocols"],
            "additionalProperties": True
        }
    
    def validate_config(self, config: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        驗證配置資料
        
        Args:
            config: 要驗證的配置字典
            
        Returns:
            Tuple[bool, List[str]]: (是否有效, 錯誤訊息列表)
        """
        errors = []
        
        if JSONSCHEMA_AVAILABLE:
            try:
                # 使用 JSON Schema 驗證
                validate(instance=config, schema=self.config_schema)
                self.logger.info("配置檔案 JSON Schema 驗證通過")
                
            except ValidationError as e:
                error_msg = f"配置檔案格式錯誤: {e.message}"
                errors.append(error_msg)
                self.logger.error(error_msg)
        else:
            # 基本驗證（不使用 jsonschema）
            self.logger.warning("jsonschema 套件未安裝，使用基本驗證。建議執行: pip install jsonschema")
            
            # 基本結構檢查
            if not isinstance(config, dict):
                errors.append("配置檔案必須是一個 JSON 物件")
            elif "protocols" not in config:
                errors.append("配置檔案缺少 'protocols' 區塊")
            elif not isinstance(config["protocols"], dict):
                errors.append("'protocols' 必須是一個物件")
        
        # 額外的業務邏輯驗證
        business_errors = self._validate_business_logic(config)
        errors.extend(business_errors)
        
        return len(errors) == 0, errors
    
    def _validate_business_logic(self, config: Dict[str, Any]) -> List[str]:
        """
        驗證業務邏輯
        
        Args:
            config: 配置字典
            
        Returns:
            List[str]: 錯誤訊息列表
        """
        errors = []
        
        if "protocols" not in config:
            errors.append("缺少 protocols 配置區塊")
            return errors
        
        protocols = config["protocols"]
        
        # 驗證串口配置
        for protocol_name in ["UART", "RTU"]:
            if protocol_name in protocols:
                protocol_config = protocols[protocol_name]
                com_port = protocol_config.get("com_port", "")
                
                # Windows 和 Linux 串口格式檢查
                if os.name == 'nt':  # Windows
                    if not (com_port.upper().startswith("COM") and com_port[3:].isdigit()):
                        errors.append(f"{protocol_name} com_port 格式錯誤，Windows 應使用 COM1, COM2 等格式")
                else:  # Linux/Unix
                    valid_prefixes = ["/dev/ttyUSB", "/dev/ttyACM", "/dev/ttyS", "/dev/serial"]
                    if not any(com_port.startswith(prefix) for prefix in valid_prefixes):
                        errors.append(f"{protocol_name} com_port 格式錯誤，Linux 應使用 /dev/ttyUSB0, /dev/ttyACM0 等格式")
        
        # 驗證網路配置
        network_protocols = ["MQTT", "FTP", "FastAPI", "TCP"]
        for protocol_name in network_protocols:
            if protocol_name in protocols:
                protocol_config = protocols[protocol_name]
                
                # 對於 MQTT，檢查 broker 欄位；對於其他協定，檢查 host 欄位
                if protocol_name == "MQTT":
                    host = protocol_config.get("broker", "")
                    host_field_name = "broker"
                else:
                    host = protocol_config.get("host", "")
                    host_field_name = "host"
                
                # 檢查主機名稱或IP格式
                if not host or host.strip() == "":
                    errors.append(f"{protocol_name} {host_field_name} 不能為空")
                
                # 檢查端口衝突
                port = protocol_config.get("port")
                if port and port < 1024 and protocol_name != "FTP":
                    errors.append(f"{protocol_name} 使用系統保留端口 {port}，建議使用 1024 以上的端口")
        
        # 檢查重複端口
        used_ports = []
        for protocol_name, protocol_config in protocols.items():
            if "port" in protocol_config:
                port = protocol_config["port"]
                if port in used_ports:
                    errors.append(f"端口 {port} 被多個協定使用，可能造成衝突")
                else:
                    used_ports.append(port)
        
        return errors
    
    def validate_config_file(self, config_file: str) -> Tuple[bool, List[str], Optional[Dict[str, Any]]]:
        """
        驗證配置檔案
        
        Args:
            config_file: 配置檔案路徑
            
        Returns:
            Tuple[bool, List[str], Optional[Dict]]: (是否有效, 錯誤訊息列表, 配置字典)
        """
        errors = []
        config = None
        
        # 檢查檔案是否存在
        if not os.path.exists(config_file):
            errors.append(f"配置檔案不存在: {config_file}")
            return False, errors, None
        
        # 讀取和解析 JSON
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
            self.logger.info(f"成功讀取配置檔案: {config_file}")
            
        except json.JSONDecodeError as e:
            error_msg = f"配置檔案 JSON 格式錯誤: {e}"
            errors.append(error_msg)
            self.logger.error(error_msg)
            return False, errors, None
        
        except Exception as e:
            error_msg = f"讀取配置檔案時發生錯誤: {e}"
            errors.append(error_msg)
            self.logger.error(error_msg)
            return False, errors, None
        
        # 驗證配置內容
        is_valid, validation_errors = self.validate_config(config)
        errors.extend(validation_errors)
        
        return is_valid, errors, config
    
    def create_default_config(self) -> Dict[str, Any]:
        """
        創建預設配置
        
        Returns:
            Dict[str, Any]: 預設配置字典
        """
        # 根據作業系統設定預設串口
        if os.name == 'nt':  # Windows
            default_uart_port = "COM3"
            default_rtu_port = "COM4"
        else:  # Linux/Unix
            default_uart_port = "/dev/ttyUSB0"
            default_rtu_port = "/dev/ttyUSB1"
        
        default_config = {
            "protocols": {
                "UART": {
                    "com_port": default_uart_port,
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
                    "com_port": default_rtu_port,
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
        
        return default_config
    
    def fix_config_issues(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        自動修復配置問題
        
        Args:
            config: 原始配置
            
        Returns:
            Dict[str, Any]: 修復後的配置
        """
        fixed_config = config.copy()
        
        # 確保必要的區塊存在
        if "protocols" not in fixed_config:
            fixed_config["protocols"] = {}
        
        # 修復串口格式
        for protocol_name in ["UART", "RTU"]:
            if protocol_name in fixed_config["protocols"]:
                protocol_config = fixed_config["protocols"][protocol_name]
                com_port = protocol_config.get("com_port", "")
                
                if os.name == 'nt' and not com_port.upper().startswith("COM"):
                    # Windows: 嘗試修復常見格式
                    if com_port.isdigit():
                        fixed_config["protocols"][protocol_name]["com_port"] = f"COM{com_port}"
                        self.logger.info(f"修復 {protocol_name} com_port: {com_port} -> COM{com_port}")
        
        # 設定預設值
        if "offline_mode" not in fixed_config:
            fixed_config["offline_mode"] = True
        
        if "data_retention_days" not in fixed_config:
            fixed_config["data_retention_days"] = 30
            
        if "max_data_points" not in fixed_config:
            fixed_config["max_data_points"] = 1000
        
        return fixed_config


def validate_and_fix_config(config_file: str, auto_fix: bool = True) -> Tuple[bool, Dict[str, Any], List[str]]:
    """
    驗證並修復配置檔案
    
    Args:
        config_file: 配置檔案路徑
        auto_fix: 是否自動修復問題
        
    Returns:
        Tuple[bool, Dict[str, Any], List[str]]: (是否成功, 配置字典, 訊息列表)
    """
    validator = ConfigValidator()
    logger = logging.getLogger(__name__)
    
    # 驗證配置檔案
    is_valid, errors, config = validator.validate_config_file(config_file)
    
    if not config:
        # 如果配置檔案無法讀取，創建預設配置
        logger.warning("無法讀取配置檔案，使用預設配置")
        config = validator.create_default_config()
        
        # 儲存預設配置
        try:
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            logger.info(f"已創建預設配置檔案: {config_file}")
            return True, config, ["已創建預設配置檔案"]
        except Exception as e:
            error_msg = f"無法儲存預設配置檔案: {e}"
            logger.error(error_msg)
            return False, config, [error_msg]
    
    if not is_valid and auto_fix:
        # 嘗試自動修復
        logger.info("嘗試自動修復配置問題")
        fixed_config = validator.fix_config_issues(config)
        
        # 重新驗證修復後的配置
        is_fixed_valid, fixed_errors = validator.validate_config(fixed_config)
        
        if is_fixed_valid:
            # 儲存修復後的配置
            try:
                with open(config_file, 'w', encoding='utf-8') as f:
                    json.dump(fixed_config, f, indent=2, ensure_ascii=False)
                logger.info("配置檔案已自動修復並儲存")
                return True, fixed_config, ["配置檔案已自動修復"]
            except Exception as e:
                error_msg = f"無法儲存修復後的配置檔案: {e}"
                logger.error(error_msg)
                return False, fixed_config, [error_msg]
        else:
            logger.warning("自動修復失敗，請手動檢查配置檔案")
            return False, config, errors + ["自動修復失敗"] + fixed_errors
    
    return is_valid, config, errors if errors else ["配置檔案驗證通過"]


if __name__ == "__main__":
    # 測試配置驗證
    import logging
    logging.basicConfig(level=logging.INFO)
    
    # 測試配置檔案
    test_config_file = "test_config.json"
    
    success, config, messages = validate_and_fix_config(test_config_file)
    
    print(f"驗證結果: {'成功' if success else '失敗'}")
    for message in messages:
        print(f"- {message}")
    
    if success:
        print("\n配置內容:")
        print(json.dumps(config, indent=2, ensure_ascii=False))
