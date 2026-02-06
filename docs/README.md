# Nexus AI Company - 文件索引

> **零員工、全智能的虛擬企業系統**
>
> 最後更新：2026-02-07 | 版本：0.8.0

---

## 快速導覽

| 我想了解... | 看這裡 |
|------------|--------|
| 專案是什麼？ | [PROJECT-WHITEPAPER.md](./PROJECT-WHITEPAPER.md) |
| 系統怎麼運作？ | [architecture/001-system-overview.md](./architecture/001-system-overview.md) |
| 為什麼這樣設計？ | [decisions/](#架構決策-adr) |
| 怎麼驗證系統？ | [scenarios/README.md](./scenarios/README.md) |
| **開發流程規範** | [protocols/agile_workflow.md](./protocols/agile_workflow.md) |
| **文件範本** | [templates/](#範本庫-templates) |
| **產品目錄** | [products/README.md](../products/README.md) |

---

## 文件結構

```
docs/
├── README.md                 ← 你在這裡
├── PROJECT-WHITEPAPER.md     # 專案白皮書（願景與目標）
│
├── architecture/             # 系統架構設計
│   ├── 001-system-overview.md
│   ├── 002-llm-abstraction.md
│   └── 003-agent-communication.md
│
├── decisions/                # 架構決策紀錄 (ADR)
│   ├── ADR-001 ~ ADR-016
│   └── ...
│
├── protocols/                # 流程規範 ✨新增
│   ├── agile_workflow.md     # 敏捷開發流程
│   └── deployment_standards.md
│
├── templates/                # 文件範本 ✨新增
│   ├── user_story_template.md
│   ├── sprint_template.md
│   └── PRD-template.md
│
├── proposals/                # 提案文件 ✨新增
│   └── PROPOSAL-001-Agile-Development-Process.md
│
├── pipelines/                # Pipeline 設計
│   ├── sales-pipeline.md
│   └── product-pipeline.md
│
├── scenarios/                # 驗證場景
│   ├── 001-sales-opportunity.yaml
│   └── 002-product-stock-crawler.yaml
│
└── engines/                  # Engine 設計（待建立）
    └── ...
```

---

## 架構決策 (ADR)

Architecture Decision Records - 記錄重要的技術決策與原因。

| ADR | 主題 | 狀態 | 摘要 |
|-----|------|------|------|
| [001](./decisions/ADR-001-tech-stack.md) | Tech Stack | 已採納 | FastAPI + Next.js + PostgreSQL |
| [002](./decisions/ADR-002-llm-priority.md) | LLM Priority | 已採納 | Claude 為主要 LLM |
| [003](./decisions/ADR-003-claude-code-execution.md) | Claude Code CLI | 已採納 | 使用 Claude Code CLI 執行複雜任務 |
| [004](./decisions/ADR-004-hybrid-execution.md) | Hybrid Execution | 已採納 | Gemini (L1) + Claude Code (L2) 混合架構 |
| [005](./decisions/ADR-005-agent-observability.md) | Agent Observability | 已採納 | 步驟執行、Action Journal、Pipeline Gate |
| [006](./decisions/ADR-006-ceo-intake.md) | CEO Intake Layer | 已採納 | GATEKEEPER 處理 CEO 非結構化輸入 |
| [007](./decisions/ADR-007-engine-layer.md) | Engine Layer | 已採納 | Agent (決策) 與 Engine (能力) 分離 |
| [008](./decisions/ADR-008-knowledge-base.md) | Knowledge Base | 已採納 | Embedding + RAG 檢索 + 內容生成（增強層）|
| [009](./decisions/ADR-009-knowledge-management.md) | Knowledge Management | 已採納 | 知識管理基礎：儲存、分類、標籤、全文搜尋 |
| [010](./decisions/ADR-010-goal-driven-execution.md) | Goal-Driven Execution | 已採納 | 目標導向執行：Goal → Phase → Checkpoint |
| [011](./decisions/ADR-011-sales-pipeline.md) | Sales Pipeline | 已採納 | 獨立銷售管理：Opportunity + MEDDIC + Pipeline Stages |
| [012](./decisions/ADR-012-product-board.md) | Product Board | 已採納 | 產品開發管理：P1-P6 階段 + QA/UAT 追蹤 |
| [013](./decisions/ADR-013-knowledge-management-simplified.md) | Knowledge Simplified | 已採納 | 簡化知識管理 |
| [014](./decisions/ADR-014-ceo-todo-refactor.md) | CEO Todo Refactor | 已採納 | CEO 待辦重構 |
| [015](./decisions/ADR-015-ceo-todo-system.md) | CEO Todo System | 已採納 | CEO 待辦系統：審批、問卷、決策 |
| [016](./decisions/ADR-016-deployer-agent.md) | Deployer Agent | 暫緩 | DEPLOYER Agent 設計（暫緩實作）|

### 新增 ADR 規範

1. 檔名格式：`ADR-XXX-簡短描述.md`
2. 必要章節：狀態、背景、決策、後果
3. 狀態選項：`草案` → `已採納` → `已棄用` → `已取代`

---

## 系統架構

### 核心元件

```
┌─────────────────────────────────────────────────────────────┐
│                        Frontend                              │
│                      (Vite + React)                          │
│   Tab: Dashboard → Sales → Project → Product → Knowledge → Inbox │
│   2.5D Office Map: Character sprites, rooms, animations      │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                        Backend                               │
│                        (FastAPI)                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                    Agents (決策層)                    │   │
│  │  HUNTER │ ORCHESTRATOR │ BUILDER │ INSPECTOR │ ...  │   │
│  └─────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                   Engines (能力層)                    │   │
│  │  MEDDIC │ NLP │ OCR │ Enrichment │ Code Analysis    │   │
│  └─────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                   Executors (執行層)                  │   │
│  │           Gemini API │ Claude Code CLI              │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    Knowledge Base                            │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌──────────┐ │
│  │ Cases      │ │ Projects   │ │ Templates  │ │Analytics │ │
│  │ (案例庫)   │ │ (專案庫)    │ │ (範本庫)   │ │(數據庫)  │ │
│  └────────────┘ └────────────┘ └────────────┘ └──────────┘ │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                       Database                               │
│              (PostgreSQL + pgvector)                         │
└─────────────────────────────────────────────────────────────┘
```

### Agent 清單

| Agent | 角色 | 職責 |
|-------|------|------|
| **HUNTER** | Sales | 商機開發、客戶跟進、MEDDIC 分析 |
| **ORCHESTRATOR** | PM | 需求分析、任務拆解、進度管理 |
| **BUILDER** | Engineer | 代碼開發、技術實作 |
| **INSPECTOR** | QA | 測試驗證、品質把關 |
| **LEDGER** | Finance | 成本估算、報價、財務追蹤 |
| **GATEKEEPER** | Admin | 行程管理、CEO 輸入處理、資訊摘要 |

### Engine 清單

| Engine | 功能 | 使用者 | 狀態 |
|--------|------|--------|------|
| **MEDDIC** | 銷售機會分析 | HUNTER | 待實作 |
| **NLP** | 意圖識別、實體抽取 | GATEKEEPER, HUNTER | 待實作 |
| **Enrichment** | 公司/聯絡人資料補全 | GATEKEEPER, HUNTER | 部分實作 |
| **OCR** | 名片、文件識別 | GATEKEEPER, LEDGER | 待實作 |
| **Code Analysis** | 代碼品質分析 | BUILDER, INSPECTOR | 待實作 |
| **Knowledge** | RAG 檢索、內容生成 | ALL | 待實作 |

---

## Pipelines

### Sales Pipeline (S1-S5)

```
S1 Lead → S2 Qualified → S3 Proposal → S4 Negotiation → S5 Closed
```
詳見：[pipelines/sales-pipeline.md](./pipelines/sales-pipeline.md)

### Product Pipeline (P1-P6)

```
P1 Requirement → P2 Analysis → P3 Development → P4 Review → P5 Testing → P6 Deployment
```
詳見：[pipelines/product-pipeline.md](./pipelines/product-pipeline.md)

---

## 驗證場景

用於測試系統流程是否正確運作。

| 場景 | Pipeline | 驗證重點 |
|------|----------|---------|
| [001-sales-opportunity](./scenarios/001-sales-opportunity.yaml) | Sales | MEDDIC 分析、Lead 處理 |
| [002-product-stock-crawler](./scenarios/002-product-stock-crawler.yaml) | Product | 需求分析、開發流程 |

詳見：[scenarios/README.md](./scenarios/README.md)

---

## 代碼對照

| 文件 | 對應代碼 |
|------|---------|
| ADR-003 Claude Code | `backend/app/executor/claude_code.py` |
| ADR-004 Hybrid | `backend/app/executor/hybrid.py` |
| ADR-005 Observability | `backend/app/core/execution_mode.py`, `action_journal.py`, `pipeline_gate.py` |
| ADR-006 CEO Intake | `backend/app/intake/`, `backend/app/api/intake.py` |
| ADR-007 Engine Layer | `backend/app/engines/` |
| ADR-010 Goal Execution | `backend/app/goals/`, `backend/app/api/goals.py` |
| ADR-011 Sales Pipeline | `backend/app/pipeline/`, `backend/app/api/pipeline.py` |
| Product Board | `backend/app/product/`, `backend/app/api/product.py` |
| Product Catalog | `backend/app/api/catalog.py`, `products/` |
| Knowledge Base | `backend/app/knowledge/`, `backend/app/api/knowledge.py` |
| Agent Configs | `backend/config/agents/*.yaml` |

### 前端元件對照

| 元件 | 路徑 | 功能 |
|------|------|------|
| SalesPipeline | `frontend/src/components/SalesPipeline.tsx` | Sales Board UI |
| GoalDashboard | `frontend/src/components/GoalDashboard.tsx` | Project Board UI |
| ProductBoard | `frontend/src/components/ProductBoard.tsx` | Product Board UI (Catalog + Pipeline 雙視圖) |
| KnowledgeBase | `frontend/src/components/KnowledgeBase.tsx` | Knowledge Base UI (Search + Markdown) |
| CEOInbox | `frontend/src/components/CEOInbox.tsx` | Inbox UI |
| OfficeMap | `frontend/src/components/OfficeMap.tsx` | 2.5D Office Map |

---

## 版本歷史

| 日期 | 版本 | 變更摘要 |
|------|------|---------|
| 2024-02-06 | 0.1.0 | 初始文件結構、ADR-001 ~ ADR-007、驗證場景 |
| 2024-02-06 | 0.2.0 | 新增 ADR-008 Knowledge Base、架構圖更新 |
| 2024-02-06 | 0.3.0 | 新增 ADR-009 Knowledge Management（知識管理基礎）|
| 2024-02-06 | 0.4.0 | 新增 ADR-010 Goal-Driven Execution（目標導向執行）|
| 2024-02-06 | 0.5.0 | 新增 ADR-011 Sales Pipeline、2.5D Office Map、Tab 順序調整 |
| 2024-02-06 | 0.6.0 | 新增 Product Board、Knowledge Base UI、Tab 更新為 6 個 |
| 2026-02-07 | 0.7.0 | 新增敏捷開發流程（整合 Product Board）、範本庫、提案系統 |
| 2026-02-07 | 0.8.0 | 新增產品目錄系統（PROPOSAL-002）、Product Catalog 視圖（PROPOSAL-003）|

---

## 前端 Tab 順序

```
[📊 Dashboard] → [💰 Sales Board] → [🎯 Project Board] → [🏭 Product Board] → [📚 Knowledge Base] → [📥 Inbox]
```

| Tab | 功能 | 對應元件 |
|-----|------|----------|
| **Dashboard** | 總覽 Agent 狀態、2.5D 辦公室地圖、KPI 指標 | `OfficeMap.tsx` |
| **Sales Board** | 商機追蹤、MEDDIC 分析、Pipeline 進度 | `SalesPipeline.tsx` |
| **Project Board** | 專案執行、Goal → Phase → Checkpoint | `GoalDashboard.tsx` |
| **Product Board** | 產品目錄（Catalog）+ 開發流程（Pipeline P1-P6） | `ProductBoard.tsx` |
| **Knowledge Base** | 知識庫、搜尋篩選、Markdown 渲染 | `KnowledgeBase.tsx` |
| **Inbox** | 新輸入處理、決策審批、Agent 請求 | `CEOInbox.tsx` |

---

## 流程規範 (Protocols)

定義開發與交付的標準流程。

| 規範 | 用途 | 相關系統 |
|------|------|----------|
| [agile_workflow.md](./protocols/agile_workflow.md) | 敏捷開發流程（整合 Product Board） | Product Board, CEO Inbox |
| [deployment_standards.md](./protocols/deployment_standards.md) | 部署規範（產品獨立部署） | - |

---

## 範本庫 (Templates)

標準化文件範本，供專案使用。

| 範本 | 用途 | 使用者 |
|------|------|--------|
| [user_story_template.md](./templates/user_story_template.md) | User Story 撰寫 | CEO, PM |
| [sprint_template.md](./templates/sprint_template.md) | Sprint 計劃追蹤 | PM |
| [PRD-template.md](./templates/PRD-template.md) | 產品需求文件 | PM |

---

## 提案文件 (Proposals)

需要 CEO 核准的設計提案。

| 提案 | 主題 | 狀態 |
|------|------|------|
| [PROPOSAL-001](./proposals/PROPOSAL-001-Agile-Development-Process.md) | 敏捷開發流程 | ✅ 已核准 |
| [PROPOSAL-002](./proposals/PROPOSAL-002-Product-Registry.md) | 產品目錄系統 | ✅ 已核准 |
| [PROPOSAL-003](./proposals/PROPOSAL-003-Product-Catalog-View.md) | Product Catalog 視圖 | ✅ 已核准 |

---

## 待辦事項

### 文件
- [ ] 補充 `docs/engines/meddic.md` - MEDDIC Engine 詳細設計
- [ ] 補充 `docs/config/` - 配置檔說明
- [ ] 補充 `docs/api/` - API 使用指南（或依賴 FastAPI `/docs`）

### 實作
- [ ] 實作 MEDDIC Engine
- [ ] 實作 NLP Engine
- [ ] 建立 Tracer Bullet 驗證流程
- [ ] 完成 Stock Crawler 場景測試

---

## 貢獻指南

### 修改文件時
1. 更新相關章節內容
2. 更新本文件的「版本歷史」
3. 如果是架構變更，建立新的 ADR

### 新增 ADR 時
1. 在 `decisions/` 建立 `ADR-XXX-名稱.md`
2. 更新本文件的「架構決策」表格
3. 如有對應代碼，更新「代碼對照」表格

---

> 📌 **維護提醒**：每次架構變更後，請更新此索引文件。
