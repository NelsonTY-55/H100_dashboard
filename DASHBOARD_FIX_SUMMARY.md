# Dashboard.py 修改總結

## 問題診斷
您遇到的問題是：
- **app_integrated.py** 在樹莓派上運行（端口5000）
- **dashboard.py** 在另一台PC上運行（端口5001）
- 兩個服務是獨立的，沒有互相通信，所以dashboard.py無法顯示樹莓派的數據

## 解決方案
我已經修改了 `dashboard.py`，讓它能夠從樹莓派獲取數據：

### 1. 新增樹莓派API連接功能
```python
# 樹莓派 API 配置
RASPBERRY_PI_CONFIG = {
    'host': '192.168.1.100',  # 請替換為您的樹莓派實際 IP 地址
    'port': 5000,
    'timeout': 10
}

def call_raspberry_pi_api(endpoint, method='GET', data=None, timeout=None):
    # 調用樹莓派 API 的函數
```

### 2. 修改主要API路由
修改了以下API來從樹莓派獲取數據：
- `/api/dashboard/stats` - 統計資料
- `/api/dashboard/chart-data` - 圖表數據
- `/api/dashboard/devices` - 設備列表

### 3. 新增配置管理
- 新增 `/api/raspberry-pi-config` API 讓您設定樹莓派IP地址
- 新增 `/raspberry-pi-config` 配置頁面
- 創建了 `raspberry_pi_config.html` 模板

## 使用步驟

### 步驟1：獲取樹莓派IP地址
在樹莓派上執行：
```bash
hostname -I
```
記下IP地址（例如：192.168.1.100）

### 步驟2：修改配置
在 `dashboard.py` 第42行，將IP地址改為您的樹莓派實際IP：
```python
RASPBERRY_PI_CONFIG = {
    'host': '192.168.1.100',  # 改為您的樹莓派IP
    'port': 5000,
    'timeout': 10
}
```

### 步驟3：確認樹莓派服務運行
確保樹莓派上的 `app_integrated.py` 正在運行：
```bash
# 在樹莓派上
python app_integrated.py
```

### 步驟4：啟動PC上的dashboard服務
```bash
# 在PC上
python dashboard.py
```

### 步驟5：訪問配置頁面
1. 瀏覽器訪問：http://localhost:5001/raspberry-pi-config
2. 輸入正確的樹莓派IP地址
3. 點擊「測試連接」確認連接正常
4. 保存設定

### 步驟6：訪問儀表板
訪問：http://localhost:5001/dashboard

## 網路需求
- 兩台設備必須連接到同一個路由器或同一個區域網路
- 不需要連接到網際網路
- 確保防火牆允許5000和5001端口通信

## 新增功能
1. **連接狀態顯示**：在儀表板上會顯示與樹莓派的連接狀態
2. **自動切換模式**：無法連接樹莓派時會顯示離線模式
3. **配置頁面**：可以隨時修改樹莓派IP地址
4. **連接測試**：可以測試與樹莓派的連接

## 故障排除
如果仍然無法連接：

1. **檢查IP地址**：確認樹莓派IP正確
2. **檢查防火牆**：
   ```bash
   # 在樹莓派上
   sudo ufw allow 5000
   ```
3. **檢查服務**：確認app_integrated.py在樹莓派上運行
4. **測試連接**：在PC的瀏覽器訪問 http://樹莓派IP:5000

## 技術改進
- 加入了requests庫用於HTTP通信
- 實現了錯誤處理和超時機制
- 提供了離線模式備援
- 新增了連接狀態監控

現在您的dashboard.py可以成功從樹莓派獲取數據並在前端顯示了。
