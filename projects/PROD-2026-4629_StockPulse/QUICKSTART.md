# StockPulse 快速啟動指南

## 前置需求

- Python 3.11+
- Node.js 18+
- npm 9+

---

## 一鍵啟動（推薦）

如果後端和前端都已在運行中，可直接存取：

| 服務 | 網址 |
|------|------|
| **StockPulse 前端** | http://localhost:5173 |
| **API 文件** | http://localhost:8001/docs |

---

## 手動啟動步驟

### Step 1: 啟動後端

```bash
# 進入後端目錄
cd /Users/manibari/Documents/Projects/nexux_company/backend

# 安裝依賴（首次執行）
pip install -r requirements.txt

# 啟動伺服器
python3 -m uvicorn app.main:app --reload --port 8001
```

**成功訊息：**
```
INFO:     Uvicorn running on http://127.0.0.1:8001 (Press CTRL+C to quit)
INFO:     Started reloader process
```

### Step 2: 啟動前端

開啟新的 Terminal：

```bash
# 進入前端目錄
cd /Users/manibari/Documents/Projects/nexux_company/frontend

# 安裝依賴（首次執行）
npm install

# 啟動開發伺服器
npm run dev
```

**成功訊息：**
```
VITE v5.x.x  ready in xxx ms

➜  Local:   http://localhost:5173/
➜  Network: use --host to expose
```

### Step 3: 開啟瀏覽器

1. 開啟 Chrome 瀏覽器
2. 前往 http://localhost:5173
3. 點擊導航列的「📈 StockPulse」Tab

---

## 驗證安裝

### 測試後端 API

```bash
# 測試搜尋 API
curl "http://localhost:8001/api/v1/stockpulse/search?q=AAPL"

# 預期回應
[{"symbol":"AAPL","name":"Apple Inc.","type":"equity"}]
```

### 測試前端

1. 在 StockPulse 頁面的搜尋框輸入 `AAPL`
2. 應該看到 Apple Inc. 的報價和 K 線圖

---

## 啟用 AI 分析（選用）

如需使用 AI 分析功能，需設定 Claude API Key：

```bash
# 設定環境變數
export ANTHROPIC_API_KEY="your-api-key-here"

# 重新啟動後端
python3 -m uvicorn app.main:app --reload --port 8001
```

---

## 常見問題

### Q1: 後端啟動失敗 - ModuleNotFoundError

**解決方案：**
```bash
pip install yfinance fastapi uvicorn numpy
```

### Q2: 前端啟動失敗 - npm ERR!

**解決方案：**
```bash
rm -rf node_modules package-lock.json
npm install
```

### Q3: 圖表不顯示

**可能原因：**
- 後端未啟動
- API 網址錯誤

**解決方案：**
1. 確認後端在 8001 埠運行
2. 檢查瀏覽器 Console 錯誤訊息

### Q4: 股票資料顯示 N/A

**可能原因：**
- 股票代碼不正確
- Yahoo Finance API 暫時無法存取

**解決方案：**
- 使用標準代碼：美股 `AAPL`、台股 `2330.TW`、港股 `0700.HK`

---

## 服務埠對照

| 服務 | 埠號 | 說明 |
|------|------|------|
| StockPulse Frontend | 5173 | React 開發伺服器 |
| StockPulse Backend | 8001 | FastAPI 伺服器 |
| Nexus Dashboard | 3000 | 主控台前端 |
| Nexus Backend | 8000 | 主控台後端 |

---

## 停止服務

在各 Terminal 中按 `Ctrl + C` 即可停止服務。

---

## 下一步

啟動成功後，請參考 `DELIVERY.md` 中的 **Demo 指引** 來體驗完整功能。
