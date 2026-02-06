# StockPulse 技術設計文件

## 1. 系統架構

```
┌─────────────────────────────────────────────────────────────────┐
│                         Client Layer                             │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  React 18 + TypeScript + Vite                           │    │
│  │  ├── TradingView Lightweight Charts (K線圖)             │    │
│  │  ├── Tailwind CSS (樣式)                                │    │
│  │  └── React Markdown (AI 回應渲染)                       │    │
│  └─────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
                              │ HTTP/REST
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                         API Layer                                │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  FastAPI (Python 3.11+)                                 │    │
│  │  ├── Pydantic (請求/回應驗證)                           │    │
│  │  ├── CORS Middleware                                    │    │
│  │  └── Async/Await 非同步處理                             │    │
│  └─────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
                              │
          ┌───────────────────┼───────────────────┐
          ▼                   ▼                   ▼
┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐
│  Yahoo Finance   │ │  TA-Lib/NumPy    │ │  Claude API      │
│  (股票資料)       │ │  (技術指標)       │ │  (AI 分析)       │
└──────────────────┘ └──────────────────┘ └──────────────────┘
```

---

## 2. 模組設計

### 2.1 後端模組結構

```
backend/app/
├── main.py                     # FastAPI 應用程式入口
├── api/
│   └── stockpulse.py           # API 路由定義
├── stockpulse/
│   ├── __init__.py
│   ├── models.py               # 資料模型 (Dataclass)
│   ├── repository.py           # 快取層
│   └── services/
│       ├── yahoo_service.py    # Yahoo Finance 封裝
│       ├── indicator_service.py # 技術指標計算
│       ├── ai_service.py       # AI 分析服務
│       └── backtest_service.py # 回測引擎
└── llm/
    ├── base.py                 # LLM 抽象介面
    └── claude.py               # Claude 實作
```

### 2.2 前端模組結構

```
frontend/src/
├── main.tsx                    # React 入口
├── App.tsx                     # 主應用 (Tab 導航)
├── vite-env.d.ts               # Vite 類型定義
└── components/
    └── stockpulse/
        ├── StockPulse.tsx      # 主容器
        ├── StockSearch.tsx     # 搜尋組件
        ├── StockChart.tsx      # K線圖表
        ├── IndicatorPanel.tsx  # 技術指標
        ├── FundamentalsPanel.tsx # 基本面
        ├── AIAnalysisPanel.tsx # AI 分析
        └── BacktestPanel.tsx   # 回測
```

---

## 3. 資料模型

### 3.1 StockQuote (即時報價)

```python
@dataclass
class StockQuote:
    symbol: str                    # 股票代碼
    name: str                      # 公司名稱
    price: float                   # 當前價格
    change: float                  # 漲跌金額
    change_percent: float          # 漲跌幅 %
    volume: int                    # 成交量
    market_cap: Optional[float]    # 市值
    pe_ratio: Optional[float]      # 本益比
    high_52w: Optional[float]      # 52週高點
    low_52w: Optional[float]       # 52週低點
    timestamp: datetime            # 報價時間
```

### 3.2 OHLCV (K線資料)

```python
@dataclass
class OHLCV:
    timestamp: datetime            # 時間
    open: float                    # 開盤價
    high: float                    # 最高價
    low: float                     # 最低價
    close: float                   # 收盤價
    volume: int                    # 成交量
```

### 3.3 TechnicalIndicators (技術指標)

```python
@dataclass
class TechnicalIndicators:
    symbol: str
    timestamp: datetime
    # 均線
    sma_20: Optional[float]
    sma_50: Optional[float]
    sma_200: Optional[float]
    # RSI
    rsi_14: Optional[float]
    # MACD
    macd_line: Optional[float]
    macd_signal: Optional[float]   # 注意：欄位名
    macd_histogram: Optional[float]
    # 布林通道
    bb_upper: Optional[float]
    bb_middle: Optional[float]
    bb_lower: Optional[float]
    # KD
    stoch_k: Optional[float]
    stoch_d: Optional[float]

    @property
    def macd_trend(self) -> str:   # 注意：用不同名稱
        """MACD 趨勢判斷"""
        ...
```

### 3.4 BacktestResult (回測結果)

```python
@dataclass
class BacktestResult:
    strategy_name: str
    symbol: str
    start_date: datetime
    end_date: datetime
    # 績效
    initial_capital: float
    final_capital: float
    total_return_pct: float
    annualized_return: float
    # 風險
    max_drawdown: float
    sharpe_ratio: float
    # 交易統計
    total_trades: int
    win_rate: float
    profit_factor: float
    # 明細
    equity_curve: List[Dict]
    trades: List[Dict]
```

---

## 4. API 規格

### 4.1 搜尋股票

```
GET /api/v1/stockpulse/search?q={query}

Response:
[
  {
    "symbol": "AAPL",
    "name": "Apple Inc.",
    "type": "equity"
  }
]
```

### 4.2 取得報價

```
GET /api/v1/stockpulse/quote/{symbol}

Response:
{
  "symbol": "AAPL",
  "name": "Apple Inc.",
  "price": 279.84,
  "change": 3.93,
  "change_percent": 1.42,
  "volume": 5199679,
  "market_cap": 4113077895168,
  ...
}
```

### 4.3 取得 K 線

```
GET /api/v1/stockpulse/ohlcv/{symbol}?period=1y&interval=1d

Response:
[
  {
    "timestamp": "2025-02-06T00:00:00",
    "time": 1738800000,
    "open": 277.16,
    "high": 279.93,
    "low": 277.00,
    "close": 279.72,
    "volume": 5220786
  }
]
```

### 4.4 取得技術指標

```
GET /api/v1/stockpulse/indicators/{symbol}

Response:
{
  "symbol": "AAPL",
  "sma": { "sma_20": 260.23, "sma_50": 268.74, "sma_200": 238.32 },
  "rsi": { "rsi_14": 75.07 },
  "macd": { "line": 2.34, "signal": -1.07, "histogram": 3.42 },
  "bollinger": { "upper": 279.10, "middle": 260.24, "lower": 241.37 },
  "stochastic": { "k": 99.71, "d": 99.71 }
}
```

### 4.5 取得基本面

```
GET /api/v1/stockpulse/fundamentals/{symbol}

Response:
{
  "symbol": "AAPL",
  "name": "Apple Inc.",
  "sector": "Technology",
  "valuation": { "pe_ratio": 35.47, "pb_ratio": 46.66, ... },
  "profitability": { "profit_margin": 0.25, "roe": 1.47, ... },
  ...
}
```

### 4.6 AI 分析

```
POST /api/v1/stockpulse/ai/analyze

Request:
{
  "symbol": "AAPL",
  "analysis_type": "combined"
}

Response:
{
  "symbol": "AAPL",
  "recommendation": "買入",
  "confidence": 0.72,
  "summary": "AAPL 技術面偏多，基本面良好",
  "bullish_factors": [...],
  "bearish_factors": [...],
  "risks": [...],
  "support_levels": [241.37, 260.24],
  "resistance_levels": [279.10, 288.62]
}
```

### 4.7 AI 選股

```
POST /api/v1/stockpulse/ai/pick

Request:
{
  "criteria": "高殖利率、低本益比",
  "market": "us",
  "limit": 5
}

Response:
{
  "criteria": "高殖利率、低本益比",
  "market": "us",
  "picks": [
    {
      "symbol": "AAPL",
      "name": "Apple Inc.",
      "price": 279.84,
      "recommendation": "買入",
      "confidence": 0.72,
      "summary": "技術面偏多..."
    }
  ],
  "timestamp": "2026-02-06T..."
}
```

### 4.8 執行回測

```
POST /api/v1/stockpulse/backtest

Request:
{
  "symbol": "AAPL",
  "strategy": "sma_crossover",
  "initial_capital": 100000,
  "fast_period": 20,
  "slow_period": 50
}

Response:
{
  "strategy_name": "SMA Crossover",
  "performance": {
    "final_capital": 120436.72,
    "total_return_pct": 20.44,
    "annualized_return": 26.37
  },
  "risk_metrics": {
    "max_drawdown": 9.02,
    "sharpe_ratio": 1.31
  },
  "trade_statistics": {
    "total_trades": 2,
    "win_rate": 50.0,
    "profit_factor": 9.22
  },
  "equity_curve": [...],
  "trades": [...]
}
```

---

## 5. 資料架構（必填章節）

> **注意：** 此章節為原技術設計遺漏，後續補充。
> 參考 `docs/protocols/data_architecture_checklist.md`

### 5.1 MVP 架構（當前實作）

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   Frontend   │────▶│   FastAPI    │────▶│ Yahoo Finance│
│   (React)    │     │   Backend    │     │    (API)     │
└──────────────┘     └──────────────┘     └──────────────┘
                            │
                            ▼
                     ┌──────────────┐
                     │ In-Memory    │
                     │ Cache (TTL)  │
                     └──────────────┘
```

**限制：**
- 無持久化儲存
- 重啟後資料遺失
- 無排程資料收集

### 5.2 建議正式版架構

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   Frontend   │────▶│   FastAPI    │────▶│    Redis     │
│   (React)    │     │   Backend    │     │   (L2 Cache) │
└──────────────┘     └──────────────┘     └──────────────┘
                            │                     │
                            ▼                     ▼
                     ┌──────────────┐     ┌──────────────┐
                     │ PostgreSQL   │     │ TimescaleDB  │
                     │ (用戶資料)    │     │ (時序資料)    │
                     └──────────────┘     └──────────────┘
                                                 ▲
                                                 │
┌──────────────┐     ┌──────────────┐            │
│ Yahoo Finance│────▶│   Celery     │────────────┘
│    (API)     │     │ (排程任務)    │
└──────────────┘     └──────────────┘
```

### 5.3 資料庫 Schema（P1 實作）

```sql
-- 股票基本資訊
CREATE TABLE stocks (
    symbol VARCHAR(20) PRIMARY KEY,
    name VARCHAR(200),
    market_type VARCHAR(10),
    sector VARCHAR(100),
    industry VARCHAR(100),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 日 K 線（TimescaleDB 超級表）
CREATE TABLE ohlcv_daily (
    symbol VARCHAR(20) NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    open DECIMAL(12,4),
    high DECIMAL(12,4),
    low DECIMAL(12,4),
    close DECIMAL(12,4),
    volume BIGINT,
    PRIMARY KEY (symbol, timestamp)
);
SELECT create_hypertable('ohlcv_daily', 'timestamp');

-- 用戶 watchlist
CREATE TABLE user_watchlist (
    user_id UUID NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    added_at TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (user_id, symbol)
);

-- 回測結果
CREATE TABLE backtest_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID,
    symbol VARCHAR(20),
    strategy VARCHAR(50),
    params JSONB,
    results JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);
```

### 5.4 排程任務設計（P1 實作）

```python
# scheduled_tasks/celery_config.py
from celery import Celery
from celery.schedules import crontab

app = Celery('stockpulse')

app.conf.beat_schedule = {
    # 每日美股收盤後更新
    'update-us-daily': {
        'task': 'tasks.fetch_us_ohlcv',
        'schedule': crontab(hour=16, minute=30, day_of_week='1-5'),
    },
    # 每日台股收盤後更新
    'update-tw-daily': {
        'task': 'tasks.fetch_tw_ohlcv',
        'schedule': crontab(hour=14, minute=0, day_of_week='1-5'),
    },
}
```

---

## 6. 快取策略

| 資料類型 | TTL | 說明 |
|----------|-----|------|
| 報價 (quote) | 15 分鐘 | 配合 Yahoo 延遲 |
| K線 (ohlcv) | 15 分鐘 | 日線資料 |
| 技術指標 | 15 分鐘 | 依賴 K 線 |
| 基本面 | 15 分鐘 | 變動頻率低 |

---

## 7. 錯誤處理

| HTTP Status | 情境 | 回應格式 |
|-------------|------|----------|
| 400 | 無效參數 | `{"detail": "Invalid symbol"}` |
| 404 | 找不到資源 | `{"detail": "Stock XXXX not found"}` |
| 500 | 伺服器錯誤 | `{"detail": "Internal server error"}` |

---

## 8. 安全考量

- [ ] API Key 環境變數管理 (ANTHROPIC_API_KEY)
- [ ] CORS 限制來源網域
- [ ] 請求速率限制 (未實作)
- [ ] 輸入驗證 (Pydantic)

---

## 9. 驗收簽核

| 角色 | 姓名 | 日期 | 簽核 |
|------|------|------|------|
| Tech Lead | - | - | ⬜ |
| Dev | - | - | ⬜ |
| DevOps | - | - | ⬜ |
