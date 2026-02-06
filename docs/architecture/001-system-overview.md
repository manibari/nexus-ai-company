# 001: 系統架構總覽

> **版本**: 1.0.0
> **日期**: 2026-02-06

---

## 架構圖

```
┌─────────────────────────────────────────────────────────────────┐
│                     FRONTEND (Vite + React)                      │
│  Tab: [Dashboard] [Sales] [Project] [Product] [Knowledge] [Inbox]│
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │ 2.5D Office │  │  HUD/KPI    │  │  Boards & Dashboards    │  │
│  │ (SVG+Chars) │  │  Dashboard  │  │  - SalesPipeline.tsx    │  │
│  └─────────────┘  └─────────────┘  │  - GoalDashboard.tsx    │  │
│                                     │  - ProductBoard.tsx     │  │
│  Office Map Features:               │  - KnowledgeBase.tsx    │  │
│  • 2.5D Character sprites           │  - CEOInbox.tsx         │  │
│  • 9 rooms with agents              └─────────────────────────┘  │
│  • Real-time status indicators                                   │
└────────────────────────────┬────────────────────────────────────┘
                             │ WebSocket + REST API
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                      BACKEND (FastAPI)                          │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                    API Layer (/api/v1)                    │   │
│  │  - GET /agents          - POST /agents/{id}/action       │   │
│  │  - GET /tasks           - POST /ceo/approve              │   │
│  │  - WS /events           - GET /dashboard/kpi             │   │
│  └──────────────────────────────────────────────────────────┘   │
│                              │                                   │
│  ┌───────────────────────────┴───────────────────────────────┐  │
│  │                     Agent Orchestrator                     │  │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐          │  │
│  │  │  Sales  │ │   PM    │ │   Eng   │ │   QA    │  ...     │  │
│  │  │  Agent  │ │  Agent  │ │  Agent  │ │  Agent  │          │  │
│  │  └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘          │  │
│  │       └───────────┴───────────┴───────────┘               │  │
│  │                        │                                   │  │
│  │              ┌─────────┴─────────┐                        │  │
│  │              │    Message Bus    │                        │  │
│  │              │  (Agent-to-Agent) │                        │  │
│  │              └───────────────────┘                        │  │
│  └───────────────────────────────────────────────────────────┘  │
│                              │                                   │
│  ┌───────────────────────────┴───────────────────────────────┐  │
│  │              Hybrid Execution Layer (ADR-004)              │  │
│  │                                                            │  │
│  │  ┌─────────────────────┐    ┌─────────────────────────┐   │  │
│  │  │    L1: Gemini API   │    │   L2: Claude Code CLI   │   │  │
│  │  │  ─────────────────  │    │  ─────────────────────  │   │  │
│  │  │  • 指令理解          │    │  • 程式碼開發            │   │  │
│  │  │  • 日常對話          │    │  • 資料查詢/爬蟲         │   │  │
│  │  │  • 簡單分析          │───▶│  • 檔案讀寫             │   │  │
│  │  │  • 任務分派          │    │  • Git 操作             │   │  │
│  │  │  (低成本)           │    │  • 系統操作 (高能力)     │   │  │
│  │  └─────────────────────┘    └─────────────────────────┘   │  │
│  └───────────────────────────────────────────────────────────┘  │
└────────────────────────────┬────────────────────────────────────┘
                             │ SQLAlchemy ORM
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                      DATABASE (SQLite)                          │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐        │
│  │  agents  │  │  tasks   │  │   logs   │  │  ledger  │        │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘        │
└─────────────────────────────────────────────────────────────────┘
```

---

## 資料流

### 1. Agent 執行週期

```
┌──────────────────────────────────────────────────────────┐
│                    Agent Think Loop                       │
│                                                           │
│   ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌──────┐  │
│   │  Sense  │───▶│  Think  │───▶│   Act   │───▶│ Log  │  │
│   │ (讀DB)  │    │ (LLM)   │    │ (Tools) │    │(寫DB)│  │
│   └─────────┘    └─────────┘    └─────────┘    └──────┘  │
│        ▲                                           │      │
│        └───────────────────────────────────────────┘      │
└──────────────────────────────────────────────────────────┘
```

### 2. CEO 決策流程

```
Agent 遇到權限不足
        │
        ▼
  建立 Blocking Task
  (status: BLOCKED_USER)
        │
        ▼
  推送到 CEO Inbox
  (WebSocket event)
        │
        ▼
  CEO 在前端審批
        │
        ▼
  POST /ceo/approve
        │
        ▼
  解除 Blocking
  Agent 繼續執行
```

---

## 核心模組說明

| 模組 | 路徑 | 職責 |
|------|------|------|
| API Layer | `backend/app/api/` | 處理 HTTP/WebSocket 請求 |
| Agent Classes | `backend/app/agents/` | 各 Agent 的思考邏輯 (GATEKEEPER, HUNTER, ORCHESTRATOR) |
| Sales Pipeline | `backend/app/pipeline/` | 商機管理 (Opportunity, Contact, Activity, MEDDIC) |
| Project Goals | `backend/app/goals/` | 專案管理 (Goal, Phase, Checkpoint) |
| Product Board | `backend/app/product/` | 產品開發 (ProductItem, P1-P6 Stages, QA/UAT) |
| Knowledge Base | `backend/app/knowledge/` | 知識庫 (KnowledgeCard, Search, Tags) |
| Engines | `backend/app/engines/` | 能力層 (MEDDIC, NLP, Enrichment) |
| LLM Providers | `backend/app/llm/` | 抽象化 LLM 調用 |
| Database | `backend/app/db/` | SQLAlchemy Models |

---

## 通訊協定

### REST API

- 用於：CRUD 操作、CEO 決策
- 格式：JSON
- 認證：MVP 階段暫無（本地運行）

### WebSocket

- 用於：即時狀態推送、RPG 畫面更新
- 事件類型：
  - `agent.status_changed`
  - `task.stage_changed`
  - `inbox.new_item`
  - `kpi.updated`

---

## 參考文件

- [ADR-001-tech-stack.md](../decisions/ADR-001-tech-stack.md)
- [002-llm-abstraction.md](./002-llm-abstraction.md)
