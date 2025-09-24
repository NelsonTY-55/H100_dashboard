# models/ftp_model.py
import os
import json
import threading
import logging


class LocalFTPServer:
    """本地FTP測試伺服器管理器"""
    
    def __init__(self):
        self.server_process = None
        self.is_running = False
        self.test_dir = "test_ftp_server"
        self.port = 2121
        self.username = "test_user"
        self.password = "test_password"
        
    def start_server(self):
        """啟動本地FTP測試伺服器"""
        if self.is_running:
            return False, "FTP伺服器已在運行中"
            
        try:
            # 建立測試目錄
            if not os.path.exists(self.test_dir):
                os.makedirs(self.test_dir)
                
            # 檢查pyftpdlib是否安裝
            try:
                import pyftpdlib
            except ImportError:
                return False, "需要安裝 pyftpdlib，請執行: pip install pyftpdlib"
            
            # 啟動FTP伺服器
            from pyftpdlib.authorizers import DummyAuthorizer
            from pyftpdlib.handlers import FTPHandler
            from pyftpdlib.servers import FTPServer
            
            authorizer = DummyAuthorizer()
            authorizer.add_user(self.username, self.password, self.test_dir, perm="elradfmwMT")
            
            handler = FTPHandler
            handler.authorizer = authorizer
            
            server = FTPServer(("127.0.0.1", self.port), handler)
            server.max_cons = 256
            server.max_cons_per_ip = 5
            
            # 在新執行緒中啟動伺服器
            def run_server():
                try:
                    server.serve_forever()
                except Exception as e:
                    print(f"FTP伺服器錯誤: {e}")
                    
            server_thread = threading.Thread(target=run_server, daemon=True)
            server_thread.start()
            
            self.is_running = True
            return True, f"本地FTP測試伺服器已啟動 (127.0.0.1:{self.port})"
            
        except Exception as e:
            return False, f"啟動FTP伺服器失敗: {str(e)}"
            
    def stop_server(self):
        """停止本地FTP測試伺服器"""
        if not self.is_running:
            return False, "FTP伺服器未運行"
            
        try:
            self.is_running = False
            return True, "本地FTP測試伺服器已停止"
        except Exception as e:
            return False, f"停止FTP伺服器失敗: {str(e)}"
            
    def get_status(self):
        """獲取伺服器狀態"""
        return {
            'is_running': self.is_running,
            'host': '127.0.0.1',
            'port': self.port,
            'username': self.username,
            'password': self.password,
            'test_dir': os.path.abspath(self.test_dir)
        }
        
    def update_config_for_test(self):
        """更新config.json為測試設定"""
        try:
            config_file = "config.json"
            if os.path.exists(config_file):
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                
                # 更新FTP設定為本地測試伺服器
                config['protocols']['FTP'] = {
                    "host": "127.0.0.1",
                    "port": self.port,
                    "username": self.username,
                    "password": self.password,
                    "remote_dir": "/",
                    "passive_mode": True
                }
                
                with open(config_file, 'w', encoding='utf-8') as f:
                    json.dump(config, f, indent=2, ensure_ascii=False)
                
                return True, "已更新config.json為測試設定"
            else:
                return False, "config.json檔案不存在"
        except Exception as e:
            return False, f"更新設定失敗: {str(e)}"


class FTPModel:
    """FTP服務模型"""
    
    def __init__(self):
        self.local_server = LocalFTPServer()
        
    def get_local_server(self):
        """獲取本地FTP服務器實例"""
        return self.local_server
        
    def start_local_server(self):
        """啟動本地FTP測試伺服器"""
        return self.local_server.start_server()
        
    def stop_local_server(self):
        """停止本地FTP測試伺服器"""
        return self.local_server.stop_server()
        
    def get_local_server_status(self):
        """獲取本地FTP伺服器狀態"""
        return self.local_server.get_status()
        
    def update_config_for_local_test(self):
        """更新設定檔為本地測試"""
        return self.local_server.update_config_for_test()