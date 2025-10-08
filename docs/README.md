# H100 Dashboard 系統

一個基於 Flask 的多協定通訊監控系統，支援 UART、MQTT、RTU、FTP、TCP 等多種通訊協定，並提供即時監控與設備管理功能。

## 功能特色

- 🌐 **多協定支援**: 支援 UART、MQTT、RTU、FTP、TCP、FastAPI 等通訊協定
- 📊 **即時監控**: 即時數據收集與顯示
- ⚙️ **設備管理**: 靈活的設備設定與配置管理
- 📈 **數據視覺化**: 直觀的 Web 介面展示系統狀態
- 📝 **歷史記錄**: 數據歷史記錄與日誌系統
- 🔄 **離線模式**: 支援離線運行模式
- 🛡️ **錯誤處理**: 完整的錯誤處理與重試機制

## 系統架構

```
H100_dashboard/
├── app_integrated_mvc.py      # 主應用程式（MVC 架構版 - 樹莓派端）
├── dashboard.py               # 儀表板 API 服務（筆電端）
├── config.json                # 主配置檔案
├── device_settings.json       # 設備設定檔案
├── multi_device_settings.json # 多設備設定檔案
├── requirements.txt           # Python 依賴套件
├── controllers/               # MVC 控制器層
├── models/                    # MVC 模型層
├── views/                     # MVC 視圖層
├── templates/                 # HTML 模板
├── config/                    # 配置檔案目錄
├── core/                      # 核心應用程式工廠
├── logs/                      # 日誌檔案
├── utils/                     # 工具模組
└── History/                   # 歷史數據
```

## 安裝與設定

### 環境需求

- Python 3.8+
- Windows 10/11
- 支援的串口設備

### 安裝步驟

1. **複製專案**
   ```bash
   git clone https://github.com/NelsonTY-55/H100_dashboard.git
   cd H100_dashboard
   ```

2. **建立虛擬環境（建議）**
   ```bash
   python -m venv venv
   venv\Scripts\activate
   ```

3. **安裝依賴套件**
   ```bash
   pip install -r requirements.txt
   ```

4. **配置設定檔案**
   - 編輯 `config.json` 設定通訊協定參數
   - 編輯 `device_settings.json` 設定設備資訊
   - 根據需求調整 `multi_device_settings.json`

## 使用方法

## 快速開始

### 部署模式（推薦）

**樹莓派端**（完整功能）：
```bash
python app_integrated_mvc.py
```

**筆電端**（API 服務）：
```bash
python dashboard.py
```

### 單一設備模式

運行完整功能在單一設備：
```bash
python app_integrated_mvc.py
```

### 存取介面

- 樹莓派端主應用: http://localhost:5000
- 筆電端 API 服務: http://localhost:5001

## 配置說明

### config.json 主要設定

```json
{
  "protocols": {
    "UART": {
      "com_port": "COM6",
      "baud_rate": 9600,
      "parity": "N",
      "stopbits": 1,
      "bytesize": 8,
      "timeout": 1
    },
    "MQTT": {
      "broker": "localhost",
      "port": 1883,
      "topic": "ct_data"
    },
    "TCP": {
      "host": "127.0.0.1",
      "port": 5020,
      "timeout": 10
    }
  },
  "offline_mode": true
}
```

### 設備設定

透過 Web 介面或直接編輯 JSON 檔案來配置設備參數。

## 主要模組說明

| 檔案 | 說明 |
|------|------|
| `app_integrated_mvc.py` | MVC 架構主應用程式（樹莓派端） |
| `dashboard.py` | API 服務（筆電端） |
| `core/app_factory.py` | Flask 應用程式工廠 |
| `controllers/` | MVC 控制器層 |
| `models/` | MVC 模型層 |
| `views/` | MVC 視圖層 |
| `multi_protocol_manager.py` | 多協定管理器 |
| `device_settings.py` | 設備設定管理 |
| `network_utils.py` | 網路工具函數 |
| `port_manager.py` | 串口管理 |
| `uart_integrated.py` | UART 通訊整合 |
| `config/config_manager.py` | 配置管理器 |

## 日誌與監控

- **應用日誌**: `logs/app_YYYYMMDD.log`
- **歷史數據**: `History/uart_data_YYYYMMDD.csv`
- **監控面板**: Flask Monitoring Dashboard 整合

## 故障排除

### 常見問題

1. **串口連接失敗**
   - 檢查串口號是否正確
   - 確認設備已正確連接
   - 檢查串口是否被其他程式佔用

2. **MQTT 連接問題**
   - 檢查 broker 地址和端口
   - 確認網路連接正常
   - 檢查防火牆設定

3. **服務啟動失敗**
   - 檢查端口是否被佔用
   - 確認 Python 環境設定正確
   - 查看日誌檔案了解詳細錯誤

### 除錯工具

```bash
# 檢查系統狀態
python check_status.py

# 測試應用程式
python test_app.py

# 除錯設備設定
python debug_device_settings.py
```

## 開發與擴展

### 新增協定支援

1. 在 `multi_protocol_manager.py` 中新增協定類別
2. 更新 `config.json` 設定結構
3. 在 Web 介面中新增相關設定頁面

### 自訂功能

可透過修改模板檔案 (`templates/`) 來自訂 Web 介面外觀和功能。

## 版本資訊

- **版本**: 1.0.0
- **Python**: 3.8+
- **Flask**: 2.0+
- **最後更新**: 2025年8月5日

## 貢獻

歡迎提交 Issues 和 Pull Requests 來改善此專案。

## 授權

此專案採用 MIT 授權條款。

## 聯絡資訊

- 專案維護者: NelsonTY-55
- GitHub: https://github.com/NelsonTY-55/H100_dashboard

---

*如有任何問題或建議，請透過 GitHub Issues 與我們聯絡。*