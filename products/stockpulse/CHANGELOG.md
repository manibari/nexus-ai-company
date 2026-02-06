# StockPulse 版本歷史

所有重要變更都會記錄在此檔案。

格式基於 [Keep a Changelog](https://keepachangelog.com/zh-TW/1.0.0/)，
版本號遵循 [Semantic Versioning](https://semver.org/lang/zh-TW/)。

---

## [1.0.0] - 2026-02-07

### 🎉 首次發布 (MVP)

**產品代號：** PROD-2026-4629

#### Added（新增）
- 股票搜尋功能（支援美股、台股、港股）
- 即時報價顯示（價格、漲跌幅、成交量、市值）
- K 線圖表（TradingView Lightweight Charts）
- 技術指標計算與顯示
  - SMA（20、50、200 日均線）
  - RSI（14 日）
  - MACD（12、26、9）
  - Bollinger Bands（20、2）
  - KD Stochastic（14、3、3）
- 基本面資料顯示
  - 估值指標（P/E、P/B、P/S）
  - 獲利能力（ROE、ROA、利潤率）
  - 成長指標（營收成長、獲利成長）
  - 股息資訊（殖利率、配發率）
  - 財務健康（流動比、負債比）
- AI 智能分析
  - Claude API 整合
  - 規則式分析備援
  - 多空因素分析
  - 操作建議與信心程度
- 策略回測
  - SMA Crossover 策略
  - RSI Reversal 策略
  - 績效指標（報酬率、夏普比率、最大回撤）
  - 權益曲線圖表
- 觀察清單功能
- Docker Compose 部署支援
- API 文件（FastAPI Swagger）

#### Fixed（修復）
- BUG-001: POST /backtest 無效策略返回 500 → 改為 400
- BUG-002: AI 分析 f-string 格式錯誤導致 500 錯誤

#### Technical（技術）
- Frontend: React 18 + Vite + TailwindCSS
- Backend: FastAPI + Python 3.11
- Charts: TradingView Lightweight Charts v4
- Data: yfinance (Yahoo Finance)
- AI: Claude API (Anthropic)

---

## 發布計劃

### [1.1.0] - 計劃中
- [ ] 用戶系統（登入、註冊）
- [ ] 持久化儲存（PostgreSQL）
- [ ] 觀察清單雲端同步

### [1.2.0] - 計劃中
- [ ] WebSocket 即時報價
- [ ] 更多技術指標
- [ ] 自訂策略回測

### [2.0.0] - 計劃中
- [ ] 付費資料源整合
- [ ] 多用戶支援
- [ ] 雲端部署（Production）

---

## 貢獻者

- PM Agent - 產品規劃、需求分析
- SWE Agent - 開發實作
- QA Agent - 測試驗證
- CEO - 需求提出、驗收
