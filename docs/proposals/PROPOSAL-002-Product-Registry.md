# 提案文件 PROPOSAL-002: 產品目錄系統

## 基本資訊

| 欄位 | 內容 |
|------|------|
| 提案 ID | PROPOSAL-002 |
| 標題 | Product Registry - 產品目錄與版本管理 |
| 提案者 | PM Agent |
| 日期 | 2026-02-07 |
| 狀態 | ✅ CEO 已核准 (2026-02-07) |

---

## 1. 問題描述

目前缺乏統一的產品清單管理：
- 已完成的產品散落在不同目錄
- 無法快速查看所有產品狀態
- 產品版本、部署資訊無統一記錄
- CEO 難以掌握公司產品全貌

---

## 2. 提案方案

### 2.1 產品目錄結構

建立 `products/` 目錄作為產品註冊中心：

```
products/
├── README.md                    # 產品總覽（主索引）
├── stockpulse/
│   ├── PRODUCT.md              # 產品資訊卡
│   ├── CHANGELOG.md            # 版本歷史
│   └── links.md                # 快速連結
└── [future-product]/
    ├── PRODUCT.md
    ├── CHANGELOG.md
    └── links.md
```

### 2.2 產品資訊卡 (PRODUCT.md)

每個產品的標準資訊：

```markdown
# [產品名稱]

## 基本資訊

| 欄位 | 內容 |
|------|------|
| 產品代號 | PROD-XXXX |
| 名稱 | [產品名稱] |
| 狀態 | 🟢 Production / 🟡 Beta / 🔵 MVP / ⚪ Deprecated |
| 版本 | v1.0.0 |
| 上線日期 | YYYY-MM-DD |

## 簡介

[一段話描述產品用途]

## 功能清單

- ✅ 功能 1
- ✅ 功能 2
- 🔄 功能 3（開發中）

## 技術架構

| 層級 | 技術 |
|------|------|
| Frontend | React / Vue / ... |
| Backend | FastAPI / Node / ... |
| Database | PostgreSQL / ... |

## 部署資訊

| 環境 | URL | 狀態 |
|------|-----|------|
| Production | https://xxx.com | 🟢 |
| Staging | https://staging.xxx.com | 🟡 |
| Development | http://localhost:XXXX | 🔵 |

## 相關連結

| 連結 | URL |
|------|-----|
| 源碼 | GitHub URL |
| 文件 | docs/ |
| API 文件 | /docs |
```

### 2.3 產品總覽 (products/README.md)

```markdown
# Nexus AI Company - 產品目錄

## 產品總覽

| 產品 | 狀態 | 版本 | 說明 |
|------|------|------|------|
| [StockPulse](./stockpulse/PRODUCT.md) | 🔵 MVP | v1.0.0 | 智能股票分析平台 |
| [產品 B](./product-b/PRODUCT.md) | 🟡 Beta | v0.5.0 | ... |

## 統計

| 指標 | 數量 |
|------|------|
| 總產品數 | X |
| Production | X |
| Beta | X |
| MVP | X |
| Deprecated | X |

## 最近更新

| 日期 | 產品 | 變更 |
|------|------|------|
| 2026-02-07 | StockPulse | v1.0.0 MVP 發布 |
```

---

## 3. 產品狀態定義

| 狀態 | 標記 | 說明 | 條件 |
|------|------|------|------|
| **Production** | 🟢 | 正式環境運行 | 有獨立網域、穩定運行 |
| **Beta** | 🟡 | 公開測試 | 功能完整、收集回饋中 |
| **MVP** | 🔵 | 最小可行產品 | 核心功能完成、本地部署 |
| **Development** | 🔧 | 開發中 | 尚未完成 MVP |
| **Deprecated** | ⚪ | 已棄用 | 不再維護 |

---

## 4. 實作計劃

### 4.1 需要建立的文件

| 文件 | 位置 | 用途 |
|------|------|------|
| `products/README.md` | 根目錄 | 產品總覽索引 |
| `products/stockpulse/PRODUCT.md` | stockpulse/ | StockPulse 產品卡 |
| `products/stockpulse/CHANGELOG.md` | stockpulse/ | 版本歷史 |

### 4.2 初始產品清單

| 產品 | 狀態 | 說明 |
|------|------|------|
| **StockPulse** | 🔵 MVP | 智能股票分析平台（已完成） |
| **Nexus Dashboard** | 🔧 Development | 內部管理系統（核心系統） |

---

## 5. 與現有系統整合

### 5.1 Product Board 整合

```
Product Board (開發追蹤)     Product Registry (產品目錄)
─────────────────────────────────────────────────────
P6 Done (完成) ─────────────▶ 新增/更新 products/xxx/
                              - 建立 PRODUCT.md
                              - 更新 CHANGELOG.md
                              - 更新 products/README.md
```

### 5.2 專案文件整合

```
projects/PROD-XXXX-xxx/      products/xxx/
────────────────────────────────────────────
開發過程文件                  產品交付文件
- PRD                        - PRODUCT.md（產品卡）
- 技術設計                    - CHANGELOG.md（版本歷史）
- Sprint 記錄                 - links.md（快速連結）
- QA 測試
- 交付文件
```

**關係：**
- `projects/` = 開發過程（歷史記錄）
- `products/` = 產品交付（現行狀態）

---

## 6. CEO 決策結果

| 問題 | 決策 | 說明 |
|------|------|------|
| Q1: 產品目錄位置 | **A** | `products/` 在根目錄 |
| Q2: 是否包含內部系統 | **B** | 包含內部系統（Nexus Dashboard）|
| Q3: CHANGELOG 詳細程度 | **B** | 詳細版（每次發布完整變更）|

**決策日期：** 2026-02-07

---

## 7. 預期效益

| 效益 | 說明 |
|------|------|
| **產品可視化** | CEO 可一目了然所有產品狀態 |
| **版本追蹤** | 完整的版本歷史記錄 |
| **快速存取** | 統一的連結索引 |
| **知識保存** | 產品資訊不隨專案結案而遺失 |

---

## 8. 簽核

| 角色 | 姓名 | 日期 | 簽核 |
|------|------|------|------|
| CEO | CEO | 2026-02-07 | ✅ 已核准 |
| PM | PM Agent | 2026-02-07 | ✅ 提案 |

---

## 附錄：StockPulse 產品卡草稿

```markdown
# StockPulse 智能股票分析平台

## 基本資訊

| 欄位 | 內容 |
|------|------|
| 產品代號 | PROD-2026-4629 |
| 名稱 | StockPulse |
| 狀態 | 🔵 MVP |
| 版本 | v1.0.0 |
| 上線日期 | 2026-02-07 |

## 簡介

一站式股票分析工具，提供即時報價、技術分析、基本面分析、
AI 智能選股與策略回測功能。

## 功能清單

- ✅ 股票搜尋（美股、台股、港股）
- ✅ 即時報價（價格、漲跌幅、成交量）
- ✅ K 線圖表（TradingView Lightweight Charts）
- ✅ 技術指標（SMA、RSI、MACD、Bollinger、KD）
- ✅ 基本面分析（估值、獲利、成長、股息）
- ✅ AI 分析（Claude API 整合）
- ✅ 策略回測（SMA Crossover、RSI Reversal）

## 技術架構

| 層級 | 技術 |
|------|------|
| Frontend | React + Vite + TailwindCSS |
| Backend | FastAPI + Python |
| Charts | TradingView Lightweight Charts |
| Data | yfinance (Yahoo Finance) |
| AI | Claude API |

## 部署資訊

| 環境 | URL | 狀態 |
|------|-----|------|
| Development | http://localhost:4000 (FE) / :4001 (BE) | 🔵 |
| Docker | docker-compose up | 🔵 |

## 相關連結

| 連結 | URL |
|------|-----|
| 源碼 | https://github.com/manibari/stockpulse |
| API 文件 | http://localhost:4001/docs |
| 專案文件 | projects/PROD-2026-4629_StockPulse/ |

## 已知限制

- 資料延遲 15 分鐘（Yahoo Finance 免費 API）
- 無用戶系統（MVP 版本）
- 無資料持久化（重啟後快取遺失）
```
