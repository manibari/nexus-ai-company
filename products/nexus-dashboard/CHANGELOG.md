# Nexus Dashboard 版本歷史

所有重要變更都會記錄在此檔案。

格式基於 [Keep a Changelog](https://keepachangelog.com/zh-TW/1.0.0/)，
版本號遵循 [Semantic Versioning](https://semver.org/lang/zh-TW/)。

---

## [0.7.0] - 2026-02-07

### Added（新增）
- 敏捷開發流程規範（整合 Product Board）
- 產品目錄系統（products/）
- User Story 範本
- Sprint 計劃範本
- 提案系統（proposals/）

### Changed（變更）
- 更新 docs/README.md 索引結構
- 新增 protocols/、templates/、proposals/ 章節

---

## [0.6.0] - 2024-02-06

### Added（新增）
- Product Board 看板（P1-P6 階段）
- Knowledge Base UI（搜尋 + Markdown 渲染）
- CEO Inbox 完整實作
- Tab 更新為 6 個

### Technical（技術）
- ADR-012: Product Board
- ADR-015: CEO Todo System

---

## [0.5.0] - 2024-02-06

### Added（新增）
- Sales Pipeline（S1-S5 銷售管道）
- 2.5D Office Map（Agent 視覺化）
- Tab 順序調整

### Technical（技術）
- ADR-011: Sales Pipeline

---

## [0.4.0] - 2024-02-06

### Added（新增）
- Goal-Driven Execution（目標導向執行）
- Project Board（Goal → Phase → Checkpoint）

### Technical（技術）
- ADR-010: Goal-Driven Execution

---

## [0.3.0] - 2024-02-06

### Added（新增）
- Knowledge Management 基礎功能
- 知識分類、標籤、全文搜尋

### Technical（技術）
- ADR-009: Knowledge Management

---

## [0.2.0] - 2024-02-06

### Added（新增）
- Knowledge Base（Embedding + RAG）
- 架構圖更新

### Technical（技術）
- ADR-008: Knowledge Base

---

## [0.1.0] - 2024-02-06

### Added（新增）
- 初始專案架構
- FastAPI 後端基礎
- React 前端基礎
- Agent 基礎框架（HUNTER、ORCHESTRATOR、GATEKEEPER）
- CEO Intake Layer
- Engine Layer 架構
- Hybrid Execution（Gemini + Claude Code）

### Technical（技術）
- ADR-001: Tech Stack（FastAPI + React + PostgreSQL）
- ADR-002: LLM Priority（Claude 為主）
- ADR-003: Claude Code CLI
- ADR-004: Hybrid Execution
- ADR-005: Agent Observability
- ADR-006: CEO Intake Layer
- ADR-007: Engine Layer

---

## 發布計劃

### [0.8.0] - 計劃中
- [ ] BUILDER Agent 實作
- [ ] INSPECTOR Agent 實作
- [ ] 自動化測試

### [0.9.0] - 計劃中
- [ ] 資料庫持久化（PostgreSQL）
- [ ] LEDGER Agent 實作
- [ ] 完整 Engine 實作

### [1.0.0] - 計劃中
- [ ] 所有核心 Agent 完成
- [ ] 自動化工作流程
- [ ] Production 部署

---

## 貢獻者

- CEO - 願景、決策
- PM Agent - 產品規劃
- SWE Agent - 開發實作
- QA Agent - 測試驗證
