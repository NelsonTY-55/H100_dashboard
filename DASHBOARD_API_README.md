# Dashboard.py 使用說明

## 概述

`dashboard.py` 是一個獨立的 Dashboard API 服務，設計用於在筆電端運行，提供遠端監控和控制功能。

## 功能特點

- 🚀 獨立運行在端口 5001
- 📊 提供系統監控 API
- 🔧 設定資訊管理
- 💓 健康檢查功能
- 🌐 支援 CORS 跨域存取
- 📝 完整的日誌記錄

## 啟動方式

### 方法 1: 直接執行
```powershell
python dashboard.py
```

### 方法 2: 透過服務管理器
```powershell
python tools/run_services.py
```

## API 端點

啟動後可在 `http://localhost:5001` 存取以下端點：

### 基本端點
- `GET /` - 服務首頁和 API 資訊
- `GET /api/health` - 健康檢查

### 資料端點
- `GET /api/system` - 系統資訊
- `GET /api/dashboard` - 儀表板資料
- `GET /api/config` - 設定資訊
- `GET /api/status` - 服務狀態

## API 回應格式

所有 API 都會回傳 JSON 格式：

```json
{
    "success": true,
    "data": { ... },
    "timestamp": "2024-10-14T14:06:34.836000"
}
```

錯誤回應：
```json
{
    "success": false,
    "error": "錯誤訊息",
    "timestamp": "2024-10-14T14:06:34.836000"
}
```

## 系統需求

### 必要套件
- Flask
- Flask-CORS
- psutil（用於系統監控）

### 選用套件
- 如果有以下模組，會提供額外功能：
  - `models.dashboard_model`
  - `models.system_model`
  - `config.config_manager`

## 使用範例

### 1. 檢查服務狀態
```bash
curl http://localhost:5001/api/health
```

### 2. 取得系統資訊
```bash
curl http://localhost:5001/api/system
```

### 3. 取得儀表板資料
```bash
curl http://localhost:5001/api/dashboard
```

## 日誌記錄

- 日誌檔案位於：`logs/dashboard_api_YYYYMMDD.log`
- 同時輸出到控制台和檔案
- 包含 INFO、WARNING、ERROR 等級別

## 錯誤處理

服務具有完善的錯誤處理機制：
- 如果部分模組無法載入，會使用基本功能
- 404 和 500 錯誤都有適當的 JSON 回應
- 所有異常都會記錄到日誌

## 測試

使用測試腳本驗證功能：
```powershell
python test_dashboard.py
```

## 部署建議

### 開發環境
```powershell
# 單獨啟動 API 服務
python dashboard.py
```

### 生產環境
```powershell
# 同時啟動主應用和 API 服務
python tools/run_services.py
```

## 故障排除

### 常見問題

1. **端口被佔用**
   ```
   錯誤: [Errno 10048] Only one usage of each socket address
   ```
   - 解決方案：更改端口或關閉佔用端口的程序

2. **模組導入失敗**
   ```
   警告: 無法導入部分模組
   ```
   - 解決方案：檢查模組路徑，服務仍可正常運行

3. **psutil 未安裝**
   ```
   note: psutil 未安裝，系統資訊有限
   ```
   - 解決方案：`pip install psutil`

### 檢查清單

- [ ] Python 3.6+ 已安裝
- [ ] 必要套件已安裝（Flask, Flask-CORS）
- [ ] 端口 5001 可用
- [ ] 專案目錄結構正確
- [ ] 有適當的檔案權限

## 更新紀錄

- **v1.0.0** (2024-10-14)
  - 初始版本
  - 基本 API 功能
  - 系統監控
  - 健康檢查
  - CORS 支援