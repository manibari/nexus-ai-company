# 001: 系統架構總覽

> **版本**: 2.0.0
> **日期**: 2026-02-07
> **變更**: SQLite → PostgreSQL + Redis; Agent Orchestrator → AgentRegistry + dispatch()

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
│  │  - GET /product         - POST /intake                   │   │
│  │  - WS /events           - GET /dashboard/kpi             │   │
│  └──────────────────────────────────────────────────────────┘   │
│                              │                                   │
│  ┌───────────────────────────┴───────────────────────────────┐  │
│  │          AgentRegistry + dispatch() (registry.py)         │  │
│  │  ┌───────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐       │  │
│  │  │GATEKEEPER │ │   PM    │ │  HUNTER  │ │   QA    │ ...   │  │
│  │  │  Agent    │ │  Agent  │ │  Agent   │ │  Agent  │       │  │
│  │  └─────┬─────┘ └────┬────┘ └────┬────┘ └────┬────┘       │  │
│  │        └─────────────┴──────────┴───────────┘             │  │
│  │                        │                                   │  │
│  │              ┌─────────┴─────────┐                        │  │
│  │              │  Redis MessageBus │                        │  │
│  │              │  (pub/sub + reply)│                        │  │
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
                             │ SQLAlchemy Async ORM
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│             DATABASE (PostgreSQL) + CACHE (Redis)                │
│                                                                  │
│  PostgreSQL:                                                     │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐             │
│  │   agents     │ │    tasks     │ │     logs     │             │
│  ├──────────────┤ ├──────────────┤ ├──────────────┤             │
│  │   ledger     │ │  inbox       │ │  ceo_todos   │             │
│  ├──────────────┤ ├──────────────┤ ├──────────────┤             │
│  │  features    │ │ ceo_inputs   │ │agent_handoffs│             │
│  ├──────────────┤ ├──────────────┤                               │
│  │activity_logs │ │product_items │                               │
│  └──────────────┘ └──────────────┘                               │
│                                                                  │
│  Redis:                                                          │
│  ┌──────────────────────────────────────────────┐               │
│  │  agent:{id}:inbox     — Agent 收件 channel    │               │
│  │  reply:{correlation}  — Request-Reply channel │               │
│  │  broadcast:all        — 廣播 channel          │               │
│  └──────────────────────────────────────────────┘               │
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

### 2. CEO 決策流程 (Feature → Product Board)

```
CEO: "StockPulse 加 AI 選股"
        │
        ▼
  GATEKEEPER: intent=product_feature → route_to=PM
        │
        ▼
  PM Agent:
  1. Gemini 生成 PRD
  2. 建立 Feature (AWAITING_APPROVAL)
  3. 建立 CEO Todo (APPROVAL)
        │
        ▼
  CEO Inbox 審核
  ├─ approve → Feature=IN_DEVELOPMENT
  │            → 建立 ProductItem (spec_ready)
  │            → Activity Log: MILESTONE
  │
  ├─ modify  → Feature=DRAFT
  └─ reject  → Feature=CANCELLED
        │
        ▼
  Product Board Pipeline (Kanban):
  spec_ready → in_progress → qa_testing → uat → done
```

### 3. Agent 通訊 (Registry + Redis)

```
intake.py → AgentRegistry.dispatch(agent_id, payload)
                    │
                    ▼
            handler.handle(payload) → Dict result
                    │
                    ▼
            Redis MessageBus (async pub/sub)
            Channel: agent:{id}:inbox
            Reply:   reply:{correlation_id}
```

---

## 核心模組說明

| 模組 | 路徑 | 職責 |
|------|------|------|
| API Layer | `backend/app/api/` | 處理 HTTP/WebSocket 請求 |
| AgentRegistry | `backend/app/agents/registry.py` | Agent 註冊 + dispatch() 統一派發 |
| MessageBus | `backend/app/agents/message_bus.py` | Redis pub/sub Agent 間通訊 |
| Agent Base | `backend/app/agents/base.py` | Sense-Think-Act 基底 + DB 方法 |
| Agent Classes | `backend/app/agents/` | GATEKEEPER, HUNTER, PM, etc. |
| Sales Pipeline | `backend/app/pipeline/` | 商機管理 (Opportunity, Contact, Activity, MEDDIC) |
| Project Goals | `backend/app/goals/` | 專案管理 (Goal, Phase, Checkpoint) |
| Product Board | `backend/app/product/` | 產品開發 (ProductItem, P1-P6 Stages, QA/UAT) |
| Knowledge Base | `backend/app/knowledge/` | 知識庫 (KnowledgeCard, Search, Tags) |
| Engines | `backend/app/engines/` | 能力層 (MEDDIC, NLP, Enrichment) |
| LLM Providers | `backend/app/llm/` | 抽象化 LLM 調用 |
| Database | `backend/app/db/` | SQLAlchemy Async Models + PostgreSQL |
| Activity Log | `backend/app/agents/activity_log.py` | Agent 活動記錄 (PostgreSQL) |

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
- [003-agent-communication.md](./003-agent-communication.md)
