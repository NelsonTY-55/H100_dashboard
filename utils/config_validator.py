#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置驗證器模組
提供配置檔案的驗證和自動修復功能
"""

import json
import os
import logging
from typing import Dict, Any, List, Optional, Tuple

def validate_and_fix_config(config_file: str, auto_fix: bool = True) -> Tuple[bool, Dict[str, Any], List[str]]:
    """
    驗證和修復配置檔案
    
    Args:
        config_file: 配置檔案路徑
        auto_fix: 是否自動修復配置
        
    Returns:
        Tuple[success, config_data, messages]
    """
    messages = []
    config_data = {}
    
    try:
        # 檢查檔案是否存在
        if not os.path.exists(config_file):
            if auto_fix:
                # 創建默認配置檔案
                default_config = get_default_config()
                with open(config_file, 'w', encoding='utf-8') as f:
                    json.dump(default_config, f, indent=2, ensure_ascii=False)
                messages.append(f"創建了默認配置檔案: {config_file}")
                return True, default_config, messages
            else:
                messages.append(f"配置檔案不存在: {config_file}")
                return False, {}, messages
        
        # 讀取配置檔案
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
        except json.JSONDecodeError as e:
            messages.append(f"JSON 格式錯誤: {e}")
            if auto_fix:
                # 嘗試備份並創建新配置
                backup_file = f"{config_file}.backup"
                os.rename(config_file, backup_file)
                default_config = get_default_config()
                with open(config_file, 'w', encoding='utf-8') as f:
                    json.dump(default_config, f, indent=2, ensure_ascii=False)
                messages.append(f"備份損壞的配置到 {backup_file}，創建新的默認配置")
                return True, default_config, messages
            else:
                return False, {}, messages
        
        # 驗證配置結構
        validation_result, fixed_config = validate_config_structure(config_data, auto_fix)
        
        if auto_fix and fixed_config != config_data:
            # 保存修復後的配置
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(fixed_config, f, indent=2, ensure_ascii=False)
            messages.append("配置已自動修復並保存")
            config_data = fixed_config
        
        if validation_result:
            messages.append("配置驗證通過")
        
        return validation_result, config_data, messages
        
    except Exception as e:
        messages.append(f"驗證配置時發生錯誤: {e}")
        return False, config_data, messages

def validate_config_structure(config: Dict[str, Any], auto_fix: bool = True) -> Tuple[bool, Dict[str, Any]]:
    """
    驗證配置結構
    
    Args:
        config: 要驗證的配置
        auto_fix: 是否自動修復
        
    Returns:
        Tuple[is_valid, fixed_config]
    """
    fixed_config = config.copy()
    is_valid = True
    
    # 必要的根級別鍵
    required_keys = {
        'general': {},
        'protocols': {},
        'database': {},
        'system': {}
    }
    
    # 檢查並添加缺失的根級別鍵
    for key, default_value in required_keys.items():
        if key not in fixed_config:
            if auto_fix:
                fixed_config[key] = default_value
            is_valid = False
    
    # 驗證 protocols 結構
    if 'protocols' in fixed_config:
        protocols_config = fixed_config['protocols']
        
        # 必要的協議配置
        required_protocols = {
            'UART': {
                'port': 'COM1',
                'baudrate': 9600,
                'timeout': 1,
                'bytesize': 8,
                'parity': 'N',
                'stopbits': 1
            },
            'FTP': {
                'host': '192.168.1.100',
                'port': 21,
                'username': 'admin',
                'password': 'password',
                'remote_dir': '/',
                'passive_mode': True
            },
            'HTTP': {
                'url': 'http://192.168.1.100:8080',
                'timeout': 10,
                'headers': {}
            }
        }
        
        for protocol, default_settings in required_protocols.items():
            if protocol not in protocols_config:
                if auto_fix:
                    protocols_config[protocol] = default_settings
                is_valid = False
            else:
                # 檢查協議內部的必要配置
                protocol_config = protocols_config[protocol]
                for setting_key, default_value in default_settings.items():
                    if setting_key not in protocol_config:
                        if auto_fix:
                            protocol_config[setting_key] = default_value
                        is_valid = False
    
    # 驗證 database 結構
    if 'database' in fixed_config:
        db_config = fixed_config['database']
        required_db_keys = {
            'type': 'sqlite',
            'host': 'localhost',
            'port': 3306,
            'database': 'h100_dashboard',
            'username': 'root',
            'password': '',
            'filename': 'dashboard.db'
        }
        
        for key, default_value in required_db_keys.items():
            if key not in db_config:
                if auto_fix:
                    db_config[key] = default_value
                is_valid = False
    
    # 驗證 system 結構
    if 'system' in fixed_config:
        system_config = fixed_config['system']
        required_system_keys = {
            'log_level': 'INFO',
            'max_log_files': 10,
            'log_file_size': '10MB',
            'enable_monitoring': True
        }
        
        for key, default_value in required_system_keys.items():
            if key not in system_config:
                if auto_fix:
                    system_config[key] = default_value
                is_valid = False
    
    return is_valid, fixed_config

def get_default_config() -> Dict[str, Any]:
    """
    獲取默認配置
    
    Returns:
        默認配置字典
    """
    return {
        "general": {
            "app_name": "H100 Dashboard",
            "version": "1.0.0",
            "description": "H100 設備監控儀表板",
            "timezone": "Asia/Taipei"
        },
        "protocols": {
            "UART": {
                "port": "COM1",
                "baudrate": 9600,
                "timeout": 1,
                "bytesize": 8,
                "parity": "N",
                "stopbits": 1,
                "enabled": True
            },
            "FTP": {
                "host": "192.168.1.100",
                "port": 21,
                "username": "admin",
                "password": "password",
                "remote_dir": "/",
                "passive_mode": True,
                "enabled": False
            },
            "HTTP": {
                "url": "http://192.168.1.100:8080",
                "timeout": 10,
                "headers": {
                    "Content-Type": "application/json"
                },
                "enabled": False
            }
        },
        "database": {
            "type": "sqlite",
            "filename": "dashboard.db",
            "host": "localhost",
            "port": 3306,
            "database": "h100_dashboard",
            "username": "root",
            "password": "",
            "pool_size": 10,
            "echo": False
        },
        "system": {
            "log_level": "INFO",
            "max_log_files": 10,
            "log_file_size": "10MB",
            "enable_monitoring": True,
            "auto_backup": True,
            "backup_interval": 24
        },
        "ui": {
            "theme": "light",
            "language": "zh-TW",
            "refresh_interval": 5,
            "chart_max_points": 1000
        }
    }