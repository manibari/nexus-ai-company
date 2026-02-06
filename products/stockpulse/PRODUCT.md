# StockPulse 智能股票分析平台

## 基本資訊

| 欄位 | 內容 |
|------|------|
| 產品代號 | PROD-2026-4629 |
| 名稱 | StockPulse |
| 狀態 | 🔵 MVP |
| 版本 | v1.0.0 |
| 上線日期 | 2026-02-07 |
| 負責 PM | PM Agent |

---

## 簡介

一站式股票分析工具，提供即時報價、技術分析、基本面分析、AI 智能選股與策略回測功能。支援美股、台股、港股市場。

---

## 功能清單

### 核心功能
- ✅ 股票搜尋（美股、台股、港股）
- ✅ 即時報價（價格、漲跌幅、成交量、市值）
- ✅ K 線圖表（TradingView Lightweight Charts）
- ✅ 技術指標（SMA、RSI、MACD、Bollinger Bands、KD）
- ✅ 基本面分析（估值、獲利、成長、股息、財務健康）
- ✅ AI 分析（Claude API 整合，規則式備援）
- ✅ 策略回測（SMA Crossover、RSI Reversal）

### 輔助功能
- ✅ 觀察清單
- ✅ 快取機制（記憶體快取）
- ✅ Docker 部署支援

---

## 技術架構

| 層級 | 技術 |
|------|------|
| Frontend | React 18 + Vite + TailwindCSS |
| Backend | FastAPI + Python 3.11 |
| Charts | TradingView Lightweight Charts v4 |
| Data Source | yfinance (Yahoo Finance API) |
| AI | Claude API (Anthropic) |
| Indicators | NumPy (TA-Lib fallback) |

### 架構圖

```
┌─────────────────────────────────────────┐
│           Frontend (React)              │
│         http://localhost:4000           │
├─────────────────────────────────────────┤
│  StockSearch │ StockChart │ Panels      │
│  IndicatorPanel │ FundamentalsPanel     │
│  AIAnalysisPanel │ BacktestPanel        │
└─────────────────┬───────────────────────┘
                  │ REST API
                  ▼
┌─────────────────────────────────────────┐
│           Backend (FastAPI)             │
│         http://localhost:4001           │
├─────────────────────────────────────────┤
│  Services:                              │
│  - YahooFinanceService (資料獲取)        │
│  - IndicatorService (技術指標計算)       │
│  - AIService (AI 分析)                  │
│  - BacktestService (策略回測)           │
├─────────────────────────────────────────┤
│  Repository: Memory Cache               │
└─────────────────────────────────────────┘
```

---

## 部署資訊

| 環境 | URL | 狀態 |
|------|-----|------|
| Development (Frontend) | http://localhost:4000 | 🔵 |
| Development (Backend) | http://localhost:4001 | 🔵 |
| Docker Compose | `docker-compose up` | 🔵 |

### 啟動方式

```bash
# 方式一：Docker Compose（推薦）
cd /Users/manibari/Documents/Projects/stockpulse
docker-compose up -d

# 方式二：本地開發
# Terminal 1 - Backend
cd backend && uvicorn main:app --reload --port 4001

# Terminal 2 - Frontend
cd frontend && npm run dev
```

---

## 相關連結

| 連結 | URL |
|------|-----|
| 源碼 | https://github.com/manibari/stockpulse |
| API 文件 | http://localhost:4001/docs |
| 專案文件 | [projects/PROD-2026-4629_StockPulse/](../../projects/PROD-2026-4629_StockPulse/) |
| 交付文件 | [DELIVERY.md](../../projects/PROD-2026-4629_StockPulse/DELIVERY.md) |
| 快速開始 | [QUICKSTART.md](../../projects/PROD-2026-4629_StockPulse/QUICKSTART.md) |

---

## API 端點

| 方法 | 端點 | 說明 |
|------|------|------|
| GET | `/api/v1/stockpulse/search?q=` | 搜尋股票 |
| GET | `/api/v1/stockpulse/quote/{symbol}` | 即時報價 |
| GET | `/api/v1/stockpulse/ohlcv/{symbol}` | 歷史 K 線 |
| GET | `/api/v1/stockpulse/indicators/{symbol}` | 技術指標 |
| GET | `/api/v1/stockpulse/fundamentals/{symbol}` | 基本面 |
| POST | `/api/v1/stockpulse/ai/analyze` | AI 分析 |
| POST | `/api/v1/stockpulse/backtest` | 策略回測 |

---

## 已知限制

| 限制 | 說明 | 未來規劃 |
|------|------|----------|
| 資料延遲 | Yahoo Finance 免費 API 延遲 15 分鐘 | 評估付費資料源 |
| 無用戶系統 | MVP 版本無登入功能 | Phase 2 加入 |
| 無持久化 | 快取重啟後遺失 | 加入 Redis/DB |
| 無即時推送 | 無 WebSocket 即時更新 | Phase 2 加入 |

---

## 版本歷史

詳見 [CHANGELOG.md](./CHANGELOG.md)
