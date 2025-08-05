# H100 Dashboard 整合使用指南

## 概述
經過整合優化後，系統現在有兩個可以同時運行的服務：

1. **主要應用程式** (`app_integrated.py`) - 端口 5000
2. **獨立Dashboard服務** (`dashboard.py`) - 端口 5001

## 架構說明

### 核心模組
- **`dashboard_service.py`** - 統一的API服務層，處理所有Dashboard相關功能
- **現有模組保持不變** - `config_manager.py`, `uart_integrated.py`, `device_settings.py` 等

### API整合
重複的API已經整合到 `dashboard_service.py` 中：
- 設備設定API (`/api/device-settings`, `/api/multi-device-settings`)
- Dashboard統計API (`/api/dashboard/stats`, `/api/dashboard/chart-data`, `/api/dashboard/devices`)
- UART相關API (`/api/uart/status`, `/api/uart/mac-ids`)
- 協定管理API (`/api/protocols`, `/api/protocol-config/<protocol>`, `/api/active-protocol`)
- 健康檢查API (`/api/health`, `/api/status`)

## 使用方式

### 1. 啟動主要應用程式 (建議)
```bash
python app_integrated.py
```
**訪問地址：** http://localhost:5000

**功能特色：**
- 完整的UART數據處理
- 協定設定和管理
- FTP服務
- WiFi連接管理
- 主機連接設定
- Flask MonitoringDashboard (如果已安裝)

### 2. 啟動獨立Dashboard服務 (可選)
```bash
python dashboard.py
```
**訪問地址：** http://localhost:5001/dashboard

**功能特色：**
- 專注於Dashboard功能
- 輕量級服務
- 適合純監控需求

### 3. 同時運行兩個服務
你可以同時運行兩個服務來獲得不同的功能：

**終端機1:**
```bash
python app_integrated.py
```

**終端機2:**
```bash
python dashboard.py
```

## 主要頁面和API

### app_integrated.py (端口 5000)
- **主頁面：** http://localhost:5000/
- **Dashboard：** http://localhost:5000/dashboard
- **設備設定：** http://localhost:5000/db-setting
- **協定設定：** http://localhost:5000/protocol-config/<protocol>
- **主機設定：** http://localhost:5000/host-config

### dashboard.py (端口 5001)
- **Dashboard：** http://localhost:5001/dashboard
- **設備設定：** http://localhost:5001/db-setting

### 共同API端點 (兩個服務都有)
- `GET /api/health` - 健康檢查
- `GET /api/status` - 服務狀態
- `GET /api/device-settings` - 獲取設備設定
- `POST /api/device-settings` - 儲存設備設定
- `GET /api/multi-device-settings` - 獲取所有設備設定
- `GET /api/dashboard/stats` - Dashboard統計資料
- `GET /api/dashboard/chart-data` - 圖表數據
- `GET /api/dashboard/devices` - 設備列表
- `GET /api/uart/status` - UART狀態
- `GET /api/uart/mac-ids` - MAC ID列表
- `GET /api/protocols` - 支援的協定列表
- `GET /api/protocol-config/<protocol>` - 協定設定
- `GET/POST /api/active-protocol` - 活躍協定

## 優化效果

### 1. 代碼重用
- 消除了重複的API實現
- 統一的錯誤處理和日誌記錄
- 一致的數據格式和響應結構

### 2. 維護性提升
- 單一數據源 (`dashboard_service.py`)
- 集中的業務邏輯
- 更容易測試和除錯

### 3. 性能優化
- 減少代碼重複
- 統一的數據獲取和處理
- 更好的資源利用

### 4. 靈活性
- 可以選擇運行完整服務或僅Dashboard
- 支持同時運行多個服務實例
- 易於擴展新功能

## 建議使用情境

### 開發和測試
- 使用 `app_integrated.py` 進行完整功能開發
- 使用 `dashboard.py` 進行Dashboard專項測試

### 生產環境
- **單一服務部署：** 只運行 `app_integrated.py`
- **微服務架構：** 同時運行兩個服務，負載均衡

### 監控和維護
- 使用 `/api/health` 和 `/api/status` 進行健康檢查
- 查看日誌輸出以監控系統狀態

## 注意事項

1. 兩個服務共享相同的配置檔案和數據源
2. 確保端口 5000 和 5001 沒有被其他應用程式占用
3. `dashboard_service.py` 是核心依賴，確保該文件正確無誤
4. 如果只需要Dashboard功能，推薦使用輕量級的 `dashboard.py`
5. 完整功能需求請使用 `app_integrated.py`

## 故障排除

### 常見問題
1. **模組導入錯誤** - 確保所有依賴模組在同一目錄
2. **端口被占用** - 檢查端口 5000/5001 是否可用
3. **API響應錯誤** - 檢查 `dashboard_service.py` 是否正常工作

### 檢查命令
```bash
# 檢查服務狀態
curl http://localhost:5000/api/health
curl http://localhost:5001/api/health

# 檢查端口使用情況
netstat -an | findstr :5000
netstat -an | findstr :5001
```
