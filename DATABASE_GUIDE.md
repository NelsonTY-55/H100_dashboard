# H100 Dashboard 資料庫功能使用指南

## 功能概述

此版本新增了完整的資料庫管理功能，允許您：

1. **自動儲存 UART 資料到 SQLite 資料庫**
2. **透過網頁介面進行資料分析**
3. **根據廠區、樓層、MAC ID、設備型號篩選資料**
4. **生成各種感測器資料的圖表**

## 新增的檔案

### 核心模組
- `database_manager.py` - 資料庫管理核心模組
- `templates/data_analysis.html` - 資料分析網頁界面
- `test_database.py` - 資料庫功能測試腳本

### 資料庫結構
系統會自動創建以下表格：

1. **uart_data** - 主要資料表
   - 儲存所有 UART 接收的感測器資料
   - 包含時間戳記、MAC ID、感測器數值等

2. **device_info** - 設備資訊表
   - 儲存設備的詳細資訊
   - 包含設備名稱、型號、位置等

3. **location_info** - 位置資訊表
   - 儲存廠區和樓層資訊

## 快速開始

### 1. 測試資料庫功能

```bash
python test_database.py
```

這會：
- 創建資料庫和表格
- 插入測試資料
- 驗證所有功能正常運作

### 2. 啟動 Dashboard 服務

```bash
python dashboard.py
```

### 3. 訪問資料分析頁面

開啟瀏覽器，前往：
```
http://localhost:5001/data-analysis
```

## 使用方法

### 資料收集

1. **自動資料儲存**
   - UART 資料會自動儲存到資料庫
   - 無需額外設定，接收到資料就會儲存

2. **手動設備註冊**
   ```python
   device_info = {
       'mac_id': 'AA:BB:CC:DD:EE:01',
       'device_name': '溫濕度感測器1',
       'device_type': 'Temperature Sensor',
       'device_model': 'H100-TH',
       'factory_area': '生產廠區A',
       'floor_level': '2F',
       'location_description': '生產線1旁'
   }
   db_manager.register_device(device_info)
   ```

### 資料分析

1. **訪問分析頁面**
   - 在側邊欄點擊「資料分析」
   - 或直接訪問 `/data-analysis`

2. **設定篩選條件**
   - 選擇廠區
   - 選擇樓層
   - 選擇 MAC ID
   - 選擇設備型號
   - 設定時間範圍

3. **選擇資料類型**
   - 溫度 (°C)
   - 濕度 (%)
   - 電壓 (V)
   - 電流 (A)
   - 功率 (W)

4. **產生圖表**
   - 點擊「產生圖表」按鈕
   - 系統會根據篩選條件查詢資料
   - 以時間序列圖表顯示結果

## API 端點

### 資料庫查詢 API

```bash
# 取得廠區列表
GET /api/database/factory-areas

# 取得樓層列表
GET /api/database/floor-levels?factory_area=廠區A

# 取得 MAC ID 列表
GET /api/database/mac-ids?factory_area=廠區A&floor_level=1F

# 取得設備型號列表
GET /api/database/device-models?mac_id=AA:BB:CC:DD:EE:01

# 取得圖表資料
GET /api/database/chart-data?factory_area=廠區A&data_type=temperature&limit=1000

# 取得統計資訊
GET /api/database/statistics

# 取得最新資料
GET /api/database/latest-data?mac_id=AA:BB:CC:DD:EE:01&limit=10
```

### 設備管理 API

```bash
# 註冊設備
POST /api/database/register-device
Content-Type: application/json
{
    "mac_id": "AA:BB:CC:DD:EE:01",
    "device_name": "溫濕度感測器1",
    "device_type": "Temperature Sensor",
    "device_model": "H100-TH",
    "factory_area": "生產廠區A",
    "floor_level": "2F"
}

# 取得設備資訊
GET /api/database/device-info?mac_id=AA:BB:CC:DD:EE:01
```

## 資料格式

### UART 資料格式

系統會自動解析以下格式的 UART 資料：

```python
{
    'timestamp': '2025-01-15 10:30:00',
    'mac_id': 'AA:BB:CC:DD:EE:01',
    'device_type': 'UART Device',
    'device_model': 'H100-001',
    'factory_area': '生產廠區A',
    'floor_level': '2F',
    'temperature': 25.5,
    'humidity': 65.2,
    'voltage': 230.1,
    'current': 5.2,
    'power': 1196.5,
    'status': 'normal'
}
```

### 圖表資料格式

圖表 API 回傳的資料格式：

```json
{
    "success": true,
    "data": [
        {
            "x": "2025-01-15T10:30:00",
            "y": 25.5,
            "mac_id": "AA:BB:CC:DD:EE:01",
            "device_model": "H100-001",
            "factory_area": "生產廠區A",
            "floor_level": "2F"
        }
    ],
    "count": 1,
    "data_type": "temperature"
}
```

## 設定說明

### 資料庫設定

預設使用 SQLite 資料庫，檔案位於：
```
uart_data.db
```

如需更改資料庫位置，修改 `database_manager.py`：

```python
db_manager = DatabaseManager(db_path="custom_path/uart_data.db")
```

### UART 資料映射

在 `uart_integrated.py` 中，您可以自訂資料映射邏輯：

```python
# 根據 channel 和 unit 設定對應的感測器數據
if parsed_data['unit'] == 'A':
    db_data['current'] = parsed_data['parameter']
elif parsed_data['unit'] == 'V':
    db_data['voltage'] = parsed_data['parameter']
elif parsed_data['channel'] == 0:  # 自訂 channel 0 為溫度
    db_data['temperature'] = parsed_data['parameter']
```

## 故障排除

### 常見問題

1. **資料庫無法創建**
   - 檢查檔案權限
   - 確保磁碟空間足夠

2. **無法訪問資料分析頁面**
   - 確認 Dashboard 服務正在運行
   - 檢查 5001 端口是否被佔用

3. **圖表沒有資料**
   - 確認資料庫中有資料
   - 檢查篩選條件是否正確
   - 確認時間範圍包含資料

4. **UART 資料未儲存**
   - 檢查 `database_manager.py` 是否正確導入
   - 查看控制台錯誤訊息

### 調試方法

1. **檢查資料庫狀態**
   ```bash
   python test_database.py
   ```

2. **檢查 API 回應**
   ```bash
   curl http://localhost:5001/api/database/statistics
   ```

3. **查看日誌**
   - Dashboard 控制台會顯示詳細的錯誤訊息
   - 資料庫操作的成功/失敗都會記錄

## 進階用法

### 自訂資料處理

您可以在接收 UART 資料時進行自訂處理：

```python
# 在 uart_integrated.py 中修改
def custom_data_processing(raw_data):
    # 自訂資料解析邏輯
    processed_data = {
        'mac_id': extract_mac_id(raw_data),
        'temperature': extract_temperature(raw_data),
        # ... 其他欄位
    }
    return processed_data
```

### 批量資料處理

```python
# 批量插入歷史資料
import csv
from database_manager import db_manager

def import_csv_data(csv_file_path):
    with open(csv_file_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            db_manager.save_uart_data(row)
```

### 資料導出

```python
# 導出特定條件的資料
def export_data(factory_area, start_time, end_time):
    data = db_manager.get_chart_data(
        factory_area=factory_area,
        start_time=start_time,
        end_time=end_time,
        limit=None  # 不限制筆數
    )
    
    # 轉換為 CSV 或其他格式
    return data
```

## 性能優化

### 資料庫索引

系統已自動創建以下索引：
- timestamp
- mac_id
- factory_area
- floor_level
- device_type

### 資料清理

建議定期清理舊資料：

```python
def cleanup_old_data(days_to_keep=30):
    cutoff_date = datetime.now() - timedelta(days=days_to_keep)
    # 實作資料清理邏輯
```

## 更新記錄

### v2.0.0 (2025-01-15)
- ✅ 新增 SQLite 資料庫支援
- ✅ 新增資料分析網頁界面
- ✅ 新增完整的 REST API
- ✅ 新增設備管理功能
- ✅ 新增圖表展示功能
- ✅ 整合 UART 資料自動儲存

### 下一版本計畫
- [ ] 支援更多資料庫類型 (MySQL, PostgreSQL)
- [ ] 新增資料導出功能
- [ ] 新增警報系統
- [ ] 新增報表生成功能
- [ ] 支援即時資料推送
