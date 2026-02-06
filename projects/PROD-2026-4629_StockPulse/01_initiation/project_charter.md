# Project Charter

## Project Information

| Field | Value |
|-------|-------|
| Project ID | PROD-2026-4629 |
| Project Name | StockPulse - 智能股票分析平台 |
| Start Date | 2026-02-06 |
| Target Release | v0.1.0 |
| Priority | High |

---

## 1. Project Purpose

為投資者提供即時報價、技術分析、基本面分析、AI 智能選股與回測功能的一站式股票分析工具。

---

## 2. Business Objectives

- 提供個人投資者專業級分析工具
- 整合 AI 智能分析降低投資決策門檻
- 建立量化回測能力驗證交易策略

---

## 3. Scope

### In Scope (Phase 1 MVP)
- 股票搜尋（代碼/名稱）
- 即時報價顯示
- K線圖表
- 技術指標（SMA, RSI, MACD, BB, KD）
- 基本面數據
- AI 分析建議
- 策略回測

### Out of Scope (Phase 2+)
- 用戶帳號系統
- Watchlist 持久化
- 回測結果儲存
- 排程資料收集
- 即時行情串流

---

## 4. Key Stakeholders

| Role | Name | Responsibility |
|------|------|----------------|
| Sponsor | CEO | 決策審批、資源配置 |
| Product Owner | PM Agent | 需求定義、優先排序 |
| Tech Lead | SWE Agent | 技術設計、實作 |
| QA Lead | QA Agent | 品質驗證、測試 |

---

## 5. Success Criteria

- [ ] 所有 P0 功能可正常運作
- [ ] API 回應時間 < 3 秒
- [ ] QA 測試通過率 > 90%
- [ ] UAT 用戶驗收通過

---

## 6. Constraints

| Type | Description |
|------|-------------|
| Data | Yahoo Finance API 延遲 15 分鐘 |
| Budget | 使用免費 API，AI 分析使用 Claude API |
| Time | MVP 2 週內完成 |

---

## 7. Assumptions

- 用戶具備基本股票知識
- 網路環境穩定
- Claude API 可用

---

## 8. Approvals

| Role | Name | Date | Signature |
|------|------|------|-----------|
| Sponsor | CEO | 2026-02-06 | ✅ Approved |
| PM | PM Agent | 2026-02-06 | ✅ |
| Tech Lead | SWE Agent | 2026-02-06 | ✅ |
