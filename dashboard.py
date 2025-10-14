#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Dashboard API 服務主程式
使用 MVC 架構的獨立 Dashboard API 服務
提供遠端監控和控制功能
"""

import os
import sys
import logging

# 設定 Python 路徑
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# 導入服務類
try:
    from services.dashboard_api_service import DashboardAPIService
    SERVICE_AVAILABLE = True
except ImportError as e:
    SERVICE_AVAILABLE = False
    print(f"警告: 無法導入 DashboardAPIService: {e}")


def main():
    """主函數"""
    if not SERVICE_AVAILABLE:
        print("❌ 無法啟動服務：DashboardAPIService 導入失敗")
        print("請檢查服務文件是否存在：services/dashboard_api_service.py")
        sys.exit(1)
    
    try:
        # 創建並啟動 API 服務
        api_service = DashboardAPIService()
        api_service.run(host='0.0.0.0', port=5001, debug=False)
        
    except Exception as e:
        print(f"❌ Dashboard API 服務啟動失敗: {e}")
        logging.error(f"Dashboard API 服務啟動失敗: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()