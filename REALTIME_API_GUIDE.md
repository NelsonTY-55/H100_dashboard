# RAS_pi 即時資料接收系統使用說明

本系統實現了從 RAS_pi 即時接收 API 資料來觸發本地 UART 掃描的功能，無需再依賴歷史資料檔案。

## 🚀 系統特色

### 核心功能
- **即時資料監控**: 定期從 RAS_pi 拉取最新 UART 資料
- **智能觸發機制**: 根據資料變化智能觸發本地 UART 掃描
- **自適應掃描**: 根據活動級別自動調整掃描頻率
- **健康監控**: 完整的系統健康狀態監控
- **錯誤恢復**: 自動重連和錯誤恢復機制

### 技術架構
1. **RAS_pi API 客戶端** (`services/raspi_api_client.py`)
2. **即時資料服務** (`services/real_time_data_service.py`)
3. **智能觸發管理器** (`services/smart_uart_trigger.py`)
4. **即時監控 API** (`controllers/realtime_api_controller.py`)

## 📊 API 端點總覽

### 系統狀態監控
```
GET /api/realtime/status           # 整體系統狀態
GET /api/realtime/raspi/status     # RAS_pi 詳細狀態
GET /api/realtime/health           # 健康檢查
GET /api/realtime/statistics       # 統計資料
```

### RAS_pi 資料獲取
```
GET /api/realtime/raspi/uart/summary                    # UART 摘要
GET /api/realtime/raspi/uart/mac-data/<mac_id>         # 特定 MAC 資料
```

### 服務控制
```
POST /api/realtime/service/start    # 啟動即時監控服務
POST /api/realtime/service/stop     # 停止即時監控服務
POST /api/realtime/trigger/start    # 啟動智能觸發管理器
POST /api/realtime/trigger/stop     # 停止智能觸發管理器
POST /api/realtime/trigger/manual   # 手動觸發掃描
```

### 配置管理
```
GET  /api/realtime/config           # 獲取配置
POST /api/realtime/config           # 更新配置
```

## ⚙️ 配置說明

系統配置位於 `config.json` 中的 `realtime_monitoring` 部分：

```json
{
  "realtime_monitoring": {
    "raspi_host": "192.168.113.239",        // RAS_pi IP 地址
    "raspi_port": 5000,                     // RAS_pi 端口
    "raspi_timeout": 10,                    // 請求超時（秒）
    "raspi_retry_count": 3,                 // 重試次數
    "realtime_poll_interval": 10,           // 輪詢間隔（秒）
    "enable_smart_trigger": true,           // 啟用智能觸發
    "min_scan_interval": 30,                // 最小掃描間隔（秒）
    "max_scan_interval": 300,               // 最大掃描間隔（秒）
    "adaptive_scanning": true,              // 自適應掃描
    "priority_mac_ids": [],                 // 優先掃描的 MAC IDs
    "auto_start_services": false            // 自動啟動服務
  }
}
```

## 🔧 使用流程

### 1. 啟動系統
```bash
python dashboard_mvc.py
```

### 2. 啟動即時監控服務
```bash
curl -X POST http://localhost:5001/api/realtime/service/start
```

### 3. 啟動智能觸發管理器
```bash
curl -X POST http://localhost:5001/api/realtime/trigger/start
```

### 4. 檢查系統狀態
```bash
curl http://localhost:5001/api/realtime/status
```

## 📈 監控和管理

### 系統健康檢查
```bash
curl http://localhost:5001/api/realtime/health
```

回應示例：
```json
{
  "success": true,
  "health": {
    "raspi_connected": true,
    "realtime_service_running": true,
    "trigger_manager_active": true,
    "overall_healthy": true
  },
  "timestamp": "2025-10-15T10:30:00"
}
```

### 獲取統計資料
```bash
curl http://localhost:5001/api/realtime/statistics
```

### 手動觸發掃描
```bash
curl -X POST http://localhost:5001/api/realtime/trigger/manual \
  -H "Content-Type: application/json" \
  -d '{"message": "測試掃描"}'
```

### 更新配置
```bash
curl -X POST http://localhost:5001/api/realtime/config \
  -H "Content-Type: application/json" \
  -d '{
    "trigger_config": {
      "min_scan_interval": 45,
      "adaptive_scanning": true
    }
  }'
```

## 🎯 觸發機制說明

### 觸發條件
1. **新 MAC ID 檢測**: 發現新的設備
2. **資料變化檢測**: 檢測到顯著的資料變化
3. **定期掃描**: 超過最大掃描間隔時間
4. **手動觸發**: 用戶手動觸發
5. **連接恢復**: RAS_pi 重新連接後

### 自適應掃描邏輯
- **高活動級別**: 頻繁觸發，掃描間隔減少
- **正常活動級別**: 標準掃描間隔
- **低活動級別**: 延長掃描間隔，節省資源

### 防重複掃描
- 最小間隔限制
- 掃描進行中時跳過新觸發
- 優先級 MAC 例外處理

## 🛠️ 故障排除

### 常見問題

1. **RAS_pi 連接失敗**
   - 檢查 IP 地址和端口配置
   - 確認 RAS_pi 服務正在運行
   - 檢查網路連通性

2. **觸發管理器無法啟動**
   - 確認即時監控服務已啟動
   - 檢查 UART 設備可用性
   - 查看日誌錯誤信息

3. **掃描未觸發**
   - 檢查觸發管理器狀態
   - 確認 RAS_pi 有資料變化
   - 檢查最小間隔設定

### 日誌查看
系統日誌會記錄在 `dashboard_mvc.log` 中，包含：
- 連接狀態變化
- 觸發事件詳情
- 掃描執行結果
- 錯誤和警告信息

## 🔍 進階功能

### 資料快取機制
- API 回應自動快取
- 可配置的 TTL 時間
- 智能快取清理

### 重試和恢復
- 自動重試機制
- 連接斷開自動恢復
- 錯誤統計和報告

### 效能優化
- 並發處理支援
- 記憶體使用優化
- 網路請求優化

## 📚 相關檔案結構

```
services/
├── raspi_api_client.py          # RAS_pi API 客戶端
├── real_time_data_service.py    # 即時資料服務
└── smart_uart_trigger.py       # 智能觸發管理器

controllers/
└── realtime_api_controller.py  # 即時監控 API 控制器

config.json                      # 系統配置文件
dashboard_mvc.py                 # 主應用程式
```

## 🎉 開始使用

1. 確保 RAS_pi 系統正在運行並可訪問
2. 修改 `config.json` 中的 RAS_pi 連接設定
3. 啟動 Dashboard 系統
4. 使用 API 端點啟動即時監控服務
5. 監控系統狀態和掃描觸發情況

這個系統讓您能夠即時接收 RAS_pi 的 API 資料，智能觸發本地 UART 掃描，實現高效的資料同步，完全無需依賴歷史資料檔案！