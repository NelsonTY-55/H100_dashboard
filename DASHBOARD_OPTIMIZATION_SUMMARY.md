# Dashboard 系統優化總結

## 優化內容

### 1. 系統架構修正
- **修正了 dashboard.py 的跨主機問題**：原本 `dashboard.py` 嘗試直接導入樹梅派上的 `uart_integrated` 模組，現在改為通過 HTTP API 獲取數據
- **添加了獨立模式支援**：通過 `DASHBOARD_STANDALONE_MODE` 環境變數控制運行模式
- **實現了模擬模組**：在無法訪問真實 UART 模組時使用 `MockUartReader` 和 `MockProtocolManager`

### 2. MAC ID 自動更新功能增強
- **改進了錯誤處理**：增加了重試邏輯，最多重試2次
- **增強了自動刷新**：實現了智能間隔調整，失敗時會延長刷新間隔
- **添加了樹梅派配置界面**：用戶可以在 `db_setting.html` 中配置樹梅派的 IP 地址和端口
- **改進了超時處理**：將超時時間從10秒延長到15秒，提高成功率

### 3. 數據獲取優化
- **多數據源支援**：優先從樹梅派獲取即時數據，失敗時回退到本地歷史文件
- **改進的 API 端點**：所有 UART 相關 API 都支援遠程轉發到樹梅派
- **增強的狀態反饋**：提供詳細的連接狀態和數據來源信息

### 4. 配置管理
- **新增配置 API**：`/api/dashboard/config` 用於獲取和更新樹梅派連接配置
- **環境變數支援**：支援通過環境變數配置系統行為
- **動態配置更新**：可以在運行時修改樹梅派連接配置

### 5. 清理了測試文件
已刪除以下不需要的測試/調試文件：
- `debug_device_settings.py`
- `debug_chart.html`
- `check_status.py`
- `app_with_settings.py`

## 使用說明

### 環境變數配置
```bash
# 設置樹梅派 IP 地址
export RASPBERRY_PI_HOST=192.168.1.100

# 設置樹梅派端口
export RASPBERRY_PI_PORT=5000

# 啟用獨立模式（推薦在監控主機上設為 true）
export DASHBOARD_STANDALONE_MODE=true
```

### 在監控主機上運行 dashboard.py
1. 確保安裝了 `requests` 模組：`pip install requests`
2. 設置環境變數或在 dashboard.py 中修改默認配置
3. 運行：`python dashboard.py`
4. 訪問 `/db-setting` 頁面配置樹梅派連接

### 在樹梅派上運行 app_integrated.py
1. 保持原有配置和運行方式
2. 確保防火牆允許來自監控主機的連接
3. 運行：`python app_integrated.py`

## 系統架構
```
監控主機 (dashboard.py)  <-- HTTP API -->  樹梅派 (app_integrated.py)
       |                                           |
   Web界面                                    UART數據接收
   設備設定                                   協定管理
   數據展示                                   數據儲存
```

## 功能改進

### MAC ID 自動更新
- 每30秒自動刷新（可動態調整）
- 失敗重試機制
- 智能間隔調整
- 多數據源支援

### 錯誤處理
- 詳細的錯誤信息
- 自動重試邏輯
- 優雅降級機制
- 狀態指示器

### 用戶界面
- 樹梅派連接配置界面
- 實時狀態反饋
- 調試面板增強
- 響應式設計

## 注意事項
1. 確保網路連接穩定
2. 檢查防火牆設置
3. 驗證 IP 地址和端口配置
4. 監控日誌輸出以便故障排除
