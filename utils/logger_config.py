#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
日誌配置模組
提供統一的日誌設定和管理
"""

import os
import logging
from datetime import datetime
from logging.handlers import TimedRotatingFileHandler, RotatingFileHandler

# 嘗試導入 colorlog，如果沒有安裝則使用標準處理器
try:
    import colorlog
    COLORLOG_AVAILABLE = True
except ImportError:
    COLORLOG_AVAILABLE = False


class LoggerConfig:
    """日誌配置管理器"""
    
    def __init__(self, log_dir: str = None, app_name: str = "app"):
        """
        初始化日誌配置
        
        Args:
            log_dir: 日誌目錄路徑
            app_name: 應用程式名稱
        """
        self.app_name = app_name
        
        # 設定日誌目錄
        if log_dir is None:
            # 根據作業系統設定預設日誌目錄
            if os.name == 'nt':  # Windows
                self.log_dir = os.path.join(os.path.expanduser("~"), "AppData", "Local", app_name, "logs")
            else:  # Linux/Unix
                self.log_dir = f"/var/log/{app_name}" if os.geteuid() == 0 else os.path.join(os.path.expanduser("~"), f".{app_name}", "logs")
        else:
            self.log_dir = log_dir
            
        # 確保日誌目錄存在
        os.makedirs(self.log_dir, exist_ok=True)
        
    def get_daily_file_handler(self, level=logging.INFO):
        """
        獲取按日期輪換的檔案處理器
        
        Args:
            level: 日誌級別
            
        Returns:
            TimedRotatingFileHandler: 日期輪換處理器
        """
        log_filename = os.path.join(self.log_dir, f"{self.app_name}_{datetime.now().strftime('%Y%m%d')}.log")
        
        handler = TimedRotatingFileHandler(
            log_filename,
            when='midnight',
            interval=1,
            backupCount=30,
            encoding='utf-8'
        )
        
        handler.setLevel(level)
        handler.setFormatter(
            logging.Formatter(
                '%(asctime)s [%(levelname)8s] [%(name)s] %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
        )
        
        # 自訂輪換檔案名稱
        handler.rotation_filename = lambda name: os.path.join(
            self.log_dir, 
            f"{self.app_name}_{datetime.now().strftime('%Y%m%d')}.log"
        )
        
        return handler
    
    def get_size_file_handler(self, max_bytes=10*1024*1024, backup_count=5, level=logging.INFO):
        """
        獲取按大小輪換的檔案處理器
        
        Args:
            max_bytes: 最大檔案大小（位元組）
            backup_count: 保留的備份檔案數量
            level: 日誌級別
            
        Returns:
            RotatingFileHandler: 大小輪換處理器
        """
        log_filename = os.path.join(self.log_dir, f"{self.app_name}.log")
        
        handler = RotatingFileHandler(
            log_filename,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
        
        handler.setLevel(level)
        handler.setFormatter(
            logging.Formatter(
                '%(asctime)s [%(levelname)8s] [%(name)s] %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
        )
        
        return handler
    
    def get_console_handler(self, level=logging.INFO):
        """
        獲取彩色控制台處理器（如果可用）或標準控制台處理器
        
        Args:
            level: 日誌級別
            
        Returns:
            StreamHandler: 控制台處理器
        """
        if COLORLOG_AVAILABLE:
            # 使用彩色日誌處理器
            handler = colorlog.StreamHandler()
            handler.setLevel(level)
            
            # 設定彩色格式
            formatter = colorlog.ColoredFormatter(
                '%(log_color)s%(asctime)s [%(levelname)8s] [%(name)s] %(message)s',
                datefmt='%H:%M:%S',
                log_colors={
                    'DEBUG': 'cyan',
                    'INFO': 'green',
                    'WARNING': 'yellow',
                    'ERROR': 'red',
                    'CRITICAL': 'red,bg_white',
                }
            )
            handler.setFormatter(formatter)
        else:
            # 使用標準日誌處理器
            handler = logging.StreamHandler()
            handler.setLevel(level)
            
            # 設定標準格式
            formatter = logging.Formatter(
                '%(asctime)s [%(levelname)8s] [%(name)s] %(message)s',
                datefmt='%H:%M:%S'
            )
            handler.setFormatter(formatter)
        
        return handler
    
    def setup_logger(self, logger_name: str = None, level=logging.INFO, 
                    use_console=True, use_file=True, use_daily_rotation=True):
        """
        設定並返回配置好的日誌記錄器
        
        Args:
            logger_name: 日誌記錄器名稱
            level: 日誌級別
            use_console: 是否使用控制台輸出
            use_file: 是否使用檔案輸出
            use_daily_rotation: 是否使用日期輪換（否則使用大小輪換）
            
        Returns:
            logging.Logger: 配置好的日誌記錄器
        """
        if logger_name is None:
            logger_name = self.app_name
            
        logger = logging.getLogger(logger_name)
        logger.setLevel(level)
        
        # 清除現有的處理器，避免重複
        logger.handlers.clear()
        
        # 添加控制台處理器
        if use_console:
            console_handler = self.get_console_handler(level)
            logger.addHandler(console_handler)
        
        # 添加檔案處理器
        if use_file:
            if use_daily_rotation:
                file_handler = self.get_daily_file_handler(level)
            else:
                file_handler = self.get_size_file_handler(level=level)
            logger.addHandler(file_handler)
        
        return logger
    
    def get_error_handler(self):
        """
        獲取專門的錯誤日誌處理器
        
        Returns:
            RotatingFileHandler: 錯誤日誌處理器
        """
        error_log_filename = os.path.join(self.log_dir, f"{self.app_name}_error.log")
        
        handler = RotatingFileHandler(
            error_log_filename,
            maxBytes=5*1024*1024,  # 5MB
            backupCount=3,
            encoding='utf-8'
        )
        
        handler.setLevel(logging.ERROR)
        handler.setFormatter(
            logging.Formatter(
                '%(asctime)s [%(levelname)8s] [%(name)s] %(filename)s:%(lineno)d - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
        )
        
        return handler


def setup_application_logging(app_name: str = "uart_monitor", log_dir: str = None, 
                            level=logging.INFO, debug_mode: bool = False):
    """
    設定應用程式的全域日誌配置
    
    Args:
        app_name: 應用程式名稱
        log_dir: 日誌目錄
        level: 日誌級別
        debug_mode: 是否為除錯模式
        
    Returns:
        logging.Logger: 主應用程式日誌記錄器
    """
    logger_config = LoggerConfig(log_dir, app_name)
    
    # 設定主日誌記錄器
    main_logger = logger_config.setup_logger(
        logger_name=app_name,
        level=level,
        use_console=True,
        use_file=True,
        use_daily_rotation=True
    )
    
    # 在除錯模式下添加錯誤處理器
    if debug_mode:
        error_handler = logger_config.get_error_handler()
        main_logger.addHandler(error_handler)
    
    # 如果 colorlog 不可用，發出警告
    if not COLORLOG_AVAILABLE:
        main_logger.warning("colorlog 套件未安裝，使用標準日誌格式。建議執行: pip install colorlog")
    
    # 設定第三方庫的日誌級別
    third_party_loggers = [
        'werkzeug', 'flask', 'urllib3', 'requests', 
        'paho.mqtt', 'pymodbus', 'pyserial'
    ]
    
    for logger_name in third_party_loggers:
        third_party_logger = logging.getLogger(logger_name)
        third_party_logger.setLevel(logging.WARNING)  # 只顯示警告以上級別
    
    return main_logger


if __name__ == "__main__":
    # 測試日誌配置
    logger = setup_application_logging("test_app", debug_mode=True)
    
    logger.debug("這是一個除錯訊息")
    logger.info("這是一個資訊訊息")
    logger.warning("這是一個警告訊息")
    logger.error("這是一個錯誤訊息")
    logger.critical("這是一個嚴重錯誤訊息")
