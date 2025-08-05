#!/usr/bin/env python3
"""
端口管理工具
用於檢查和處理端口占用問題
"""

import socket
import subprocess
import sys
import platform
import logging
from typing import List, Tuple, Optional

class PortManager:
    """端口管理器"""
    
    @staticmethod
    def check_port_available(host: str, port: int, timeout: float = 1.0) -> bool:
        """
        檢查端口是否可用
        
        Args:
            host: 主機地址
            port: 端口號
            timeout: 超時時間
            
        Returns:
            bool: True 表示端口可用，False 表示被占用
        """
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex((host, port))
            sock.close()
            return result != 0  # 連接失敗表示端口可用
        except Exception as e:
            logging.warning(f"檢查端口 {host}:{port} 時發生錯誤: {e}")
            return False
    
    @staticmethod
    def find_available_port(host: str, start_port: int, max_attempts: int = 20) -> Optional[int]:
        """
        尋找可用的端口
        
        Args:
            host: 主機地址
            start_port: 起始端口
            max_attempts: 最大嘗試次數
            
        Returns:
            Optional[int]: 可用的端口號，如果找不到則返回 None
        """
        for i in range(max_attempts):
            port = start_port + i
            if 1 <= port <= 65535 and PortManager.check_port_available(host, port):
                return port
        return None
    
    @staticmethod
    def get_port_process_info(port: int) -> List[dict]:
        """
        獲取占用指定端口的進程信息
        
        Args:
            port: 端口號
            
        Returns:
            List[dict]: 進程信息列表
        """
        processes = []
        
        try:
            if platform.system() == "Windows":
                # Windows 使用 netstat
                cmd = ["netstat", "-ano"]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
                
                for line in result.stdout.split('\n'):
                    if f":{port}" in line and "LISTENING" in line:
                        parts = line.split()
                        if len(parts) >= 5:
                            pid = parts[-1]
                            processes.append({
                                'pid': pid,
                                'protocol': parts[0],
                                'address': parts[1],
                                'state': parts[3] if len(parts) > 3 else 'UNKNOWN'
                            })
            else:
                # Linux/Unix 使用 lsof 或 netstat
                try:
                    cmd = ["lsof", f"-i:{port}"]
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
                    
                    for line in result.stdout.split('\n')[1:]:  # 跳過標題行
                        if line.strip():
                            parts = line.split()
                            if len(parts) >= 2:
                                processes.append({
                                    'command': parts[0],
                                    'pid': parts[1],
                                    'user': parts[2] if len(parts) > 2 else 'unknown',
                                    'address': parts[8] if len(parts) > 8 else 'unknown'
                                })
                except FileNotFoundError:
                    # 如果沒有 lsof，嘗試使用 netstat
                    cmd = ["netstat", "-tlnp"]
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
                    
                    for line in result.stdout.split('\n'):
                        if f":{port}" in line and "LISTEN" in line:
                            parts = line.split()
                            if len(parts) >= 7:
                                pid_program = parts[6].split('/')
                                processes.append({
                                    'pid': pid_program[0] if pid_program[0] != '-' else 'unknown',
                                    'command': pid_program[1] if len(pid_program) > 1 else 'unknown',
                                    'address': parts[3]
                                })
                                
        except Exception as e:
            logging.warning(f"獲取端口 {port} 的進程信息時發生錯誤: {e}")
        
        return processes
    
    @staticmethod
    def kill_process_by_port(port: int, force: bool = False) -> bool:
        """
        終止占用指定端口的進程
        
        Args:
            port: 端口號
            force: 是否強制終止
            
        Returns:
            bool: 是否成功終止進程
        """
        try:
            processes = PortManager.get_port_process_info(port)
            
            if not processes:
                logging.info(f"端口 {port} 沒有被任何進程占用")
                return True
            
            success_count = 0
            
            for proc in processes:
                pid = proc.get('pid')
                if pid and pid != 'unknown' and pid.isdigit():
                    try:
                        pid = int(pid)
                        
                        if platform.system() == "Windows":
                            cmd = ["taskkill", "/F" if force else "", "/PID", str(pid)]
                            cmd = [x for x in cmd if x]  # 移除空字符串
                        else:
                            cmd = ["kill", "-9" if force else "-TERM", str(pid)]
                        
                        result = subprocess.run(cmd, capture_output=True, timeout=5)
                        
                        if result.returncode == 0:
                            logging.info(f"成功終止進程 PID {pid} (端口 {port})")
                            success_count += 1
                        else:
                            logging.warning(f"終止進程 PID {pid} 失敗: {result.stderr.decode()}")
                            
                    except Exception as e:
                        logging.warning(f"終止進程 PID {pid} 時發生錯誤: {e}")
            
            return success_count > 0
            
        except Exception as e:
            logging.error(f"終止端口 {port} 的進程時發生錯誤: {e}")
            return False
    
    @staticmethod
    def cleanup_port(host: str, port: int) -> bool:
        """
        清理端口（嘗試釋放占用的端口）
        
        Args:
            host: 主機地址
            port: 端口號
            
        Returns:
            bool: 是否成功清理
        """
        try:
            # 首先檢查端口是否真的被占用
            if PortManager.check_port_available(host, port):
                logging.info(f"端口 {host}:{port} 已經可用")
                return True
            
            logging.info(f"嘗試清理端口 {host}:{port}...")
            
            # 獲取占用進程信息
            processes = PortManager.get_port_process_info(port)
            
            if processes:
                logging.info(f"發現 {len(processes)} 個進程占用端口 {port}:")
                for proc in processes:
                    logging.info(f"  - PID: {proc.get('pid', 'unknown')}, "
                               f"Command: {proc.get('command', 'unknown')}")
                
                # 嘗試優雅終止進程
                if PortManager.kill_process_by_port(port, force=False):
                    import time
                    time.sleep(2)  # 等待進程結束
                    
                    # 檢查是否成功釋放
                    if PortManager.check_port_available(host, port):
                        logging.info(f"端口 {port} 已成功釋放")
                        return True
                    else:
                        # 強制終止
                        logging.warning(f"優雅終止失敗，嘗試強制終止端口 {port} 的進程")
                        if PortManager.kill_process_by_port(port, force=True):
                            time.sleep(2)
                            if PortManager.check_port_available(host, port):
                                logging.info(f"端口 {port} 已強制釋放")
                                return True
            
            # 嘗試使用 socket 選項強制釋放
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                if platform.system() != "Windows":
                    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
                
                sock.bind((host, port))
                sock.close()
                
                import time
                time.sleep(1)
                
                if PortManager.check_port_available(host, port):
                    logging.info(f"端口 {port} 通過 socket 選項成功釋放")
                    return True
                    
            except Exception as e:
                logging.warning(f"使用 socket 選項清理端口失敗: {e}")
            
            logging.error(f"無法清理端口 {host}:{port}")
            return False
            
        except Exception as e:
            logging.error(f"清理端口時發生錯誤: {e}")
            return False

def main():
    """主函數 - 端口工具命令行界面"""
    import argparse
    
    parser = argparse.ArgumentParser(description='端口管理工具')
    parser.add_argument('--check', type=int, help='檢查指定端口是否可用')
    parser.add_argument('--find', type=int, help='從指定端口開始尋找可用端口')
    parser.add_argument('--info', type=int, help='獲取占用指定端口的進程信息')
    parser.add_argument('--kill', type=int, help='終止占用指定端口的進程')
    parser.add_argument('--cleanup', type=int, help='清理指定端口')
    parser.add_argument('--host', default='localhost', help='主機地址 (預設: localhost)')
    parser.add_argument('--force', action='store_true', help='強制執行')
    
    args = parser.parse_args()
    
    # 設定日誌
    logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
    
    if args.check:
        available = PortManager.check_port_available(args.host, args.check)
        print(f"端口 {args.host}:{args.check} {'可用' if available else '被占用'}")
        
    elif args.find:
        port = PortManager.find_available_port(args.host, args.find)
        if port:
            print(f"找到可用端口: {args.host}:{port}")
        else:
            print(f"從 {args.find} 開始找不到可用端口")
            
    elif args.info:
        processes = PortManager.get_port_process_info(args.info)
        if processes:
            print(f"端口 {args.info} 的占用進程:")
            for proc in processes:
                print(f"  PID: {proc.get('pid', 'unknown')}, "
                     f"Command: {proc.get('command', 'unknown')}")
        else:
            print(f"端口 {args.info} 沒有被占用")
            
    elif args.kill:
        success = PortManager.kill_process_by_port(args.kill, args.force)
        print(f"終止端口 {args.kill} 的進程: {'成功' if success else '失敗'}")
        
    elif args.cleanup:
        success = PortManager.cleanup_port(args.host, args.cleanup)
        print(f"清理端口 {args.host}:{args.cleanup}: {'成功' if success else '失敗'}")
        
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
