# 🍓 樹莓派部署指南 - app_integrated_mvc.py

## 📋 修改摘要

### ✅ 已完成的優化：
1. **端口修改**: 從 5001 改為 5000，避免與其他主機的 dashboard.py 衝突
2. **平台適配**: 自動檢測 Linux/樹莓派系統並使用適當的路徑
3. **日誌優化**: 樹莓派使用 `/home/pi/my_fastapi_app/logs` 路徑
4. **系統資訊**: 顯示運行平台信息

## 🚀 在樹莓派上部署

### 1. 系統準備
```bash
# 更新系統
sudo apt update && sudo apt upgrade -y

# 安裝 Python 和相關工具
sudo apt install python3-pip python3-venv git -y

# 創建日誌目錄並設定權限
sudo mkdir -p /home/pi/my_fastapi_app/logs
sudo chown pi:pi /home/pi/my_fastapi_app/logs
```

### 2. 專案部署
```bash
# 克隆專案（如果需要）
cd /home/pi
git clone <your-repo-url> H100_dashboard
cd H100_dashboard

# 安裝依賴
pip3 install -r requirements.txt

# 設定執行權限
chmod +x app_integrated_mvc.py
```

### 3. 啟動服務
```bash
# 直接啟動
python3 app_integrated_mvc.py

# 或使用 nohup 在後台運行
nohup python3 app_integrated_mvc.py > /home/pi/app_output.log 2>&1 &
```

### 4. 驗證部署
```bash
# 檢查服務是否啟動
ps aux | grep app_integrated_mvc

# 檢查端口是否監聽
sudo netstat -tulpn | grep 5000

# 測試 API 端點
curl http://localhost:5000/api/health
```

## 🌐 網路配置

### 樹莓派服務 (端口 5000)
- **主應用程式**: `http://[樹莓派IP]:5000`
- **API 端點**: `http://[樹莓派IP]:5000/api/*`
- **Dashboard**: `http://[樹莓派IP]:5000/dashboard`
- **設備設定**: `http://[樹莓派IP]:5000/db-setting`

### 其他主機 Dashboard 服務 (端口 5001)
- **Dashboard 監控**: `http://[其他主機IP]:5001/dashboard`

## 📁 日誌管理

### 日誌位置
- **Windows**: `./logs/app_YYYYMMDD.log`
- **Linux/樹莓派**: `/home/pi/my_fastapi_app/logs/app_YYYYMMDD.log`

### 日誌特性
- 自動按日期切換
- 保留 30 天歷史記錄
- UTF-8 編碼支援

## 🔧 系統服務化 (可選)

如果需要將應用程式設定為系統服務：

1. **創建服務文件**:
```bash
sudo nano /etc/systemd/system/h100-dashboard.service
```

2. **服務配置內容**:
```ini
[Unit]
Description=H100 Dashboard Service
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/H100_dashboard
ExecStart=/usr/bin/python3 /home/pi/H100_dashboard/app_integrated_mvc.py
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

3. **啟用和啟動服務**:
```bash
sudo systemctl daemon-reload
sudo systemctl enable h100-dashboard.service
sudo systemctl start h100-dashboard.service

# 檢查狀態
sudo systemctl status h100-dashboard.service
```

## 🛠️ 故障排除

### 常見問題

1. **端口被佔用**:
```bash
sudo lsof -i :5000
sudo kill -9 <PID>
```

2. **權限問題**:
```bash
sudo chown -R pi:pi /home/pi/H100_dashboard
sudo chmod -R 755 /home/pi/H100_dashboard
```

3. **依賴缺失**:
```bash
pip3 install --upgrade pip
pip3 install -r requirements.txt --force-reinstall
```

4. **日誌權限問題**:
```bash
sudo mkdir -p /home/pi/my_fastapi_app/logs
sudo chown pi:pi /home/pi/my_fastapi_app/logs
sudo chmod 755 /home/pi/my_fastapi_app/logs
```

## 📊 性能監控

```bash
# 查看系統資源使用
htop

# 查看應用程式記憶體使用
ps aux | grep app_integrated_mvc

# 查看網路連接
sudo netstat -tulpn | grep python3
```

## 🔗 相關文件
- `app_integrated_mvc.py` - 主應用程式（樹莓派優化版）
- `test_pi_deployment.py` - 部署測試腳本
- `models/logging_model.py` - 日誌管理模型（已優化）
- `requirements.txt` - 依賴套件列表