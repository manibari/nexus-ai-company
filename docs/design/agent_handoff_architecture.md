# Agent Handoff Architecture

**版本**: 1.0
**日期**: 2026-02-07
**狀態**: 已實作 (Step 1~4 完成)

---

## 1. 系統架構

```
                           ┌──────────────┐
                           │   Frontend   │
                           │  (React/TS)  │
                           └──────┬───────┘
                                  │ HTTP API
                           ┌──────▼───────┐
                           │   FastAPI    │
                           │  (Backend)   │
                           └──────┬───────┘
                                  │
              ┌───────────────────┼───────────────────┐
              │                   │                   │
     ┌────────▼────────┐  ┌──────▼───────┐  ┌────────▼────────┐
     │  Agent Registry  │  │  Message Bus │  │  Activity Log   │
     │  (Dispatcher)    │  │  (Redis)     │  │  (PostgreSQL)   │
     └────────┬────────┘  └──────┬───────┘  └─────────────────┘
              │                  │
     ┌────────▼──────────────────▼────────┐
     │           Agent Layer              │
     │                                     │
     │  ┌────────────┐  ┌──────────────┐  │
     │  │ GATEKEEPER │  │     PM       │  │
     │  │ (意圖分析)  │  │ (產品管理)   │  │
     │  └────────────┘  └──────────────┘  │
     │  ┌────────────┐  ┌──────────────┐  │
     │  │  HUNTER    │  │ ORCHESTRATOR │  │
     │  │ (銷售追蹤)  │  │ (專案協調)   │  │
     │  └────────────┘  └──────────────┘  │
     └────────────────────────────────────┘
              │                  │
     ┌────────▼──────────────────▼────────┐
     │          Data Layer                │
     │                                     │
     │  ┌──────────┐  ┌───────────────┐   │
     │  │PostgreSQL│  │    Redis      │   │
     │  │ (持久化)  │  │ (訊息/快取)   │   │
     │  └──────────┘  └───────────────┘   │
     └────────────────────────────────────┘
```

### 元件說明

| 元件 | 職責 | 檔案 |
|------|------|------|
| **Agent Registry** | 註冊、查詢、派發 Agent | `backend/app/agents/registry.py` |
| **Message Bus** | Agent 間非同步通訊（pub/sub, request-reply） | `backend/app/agents/message_bus.py` |
| **Activity Log** | 記錄所有 Agent 活動 | `backend/app/agents/activity_log.py` |
| **GATEKEEPER** | 接收 CEO 輸入、意圖識別、路由決策 | `backend/app/agents/gatekeeper.py` |
| **PM** | 產品功能需求管理、PRD 撰寫 | `backend/app/agents/pm.py` |
| **HUNTER** | 商機追蹤、MEDDIC 分析 | `backend/app/agents/hunter.py` |
| **ORCHESTRATOR** | 專案分解、進度追蹤 | `backend/app/agents/orchestrator.py` |

---

## 2. Agent 互轉流程

### 2.1 主要流程：CEO Input → Agent 處理

```
CEO (Frontend)
  │
  │ POST /api/v1/intake/input
  ▼
┌─────────────┐
│  intake.py  │ ─── 記錄 CEO Activity Log
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ GATEKEEPER  │ ─── 意圖識別 (Gemini 2.5 Flash)
│  .analyze() │     實體解析
└──────┬──────┘     路由決策
       │
       │ route_to = "PM" / "HUNTER" / "ORCHESTRATOR"
       ▼
┌─────────────┐
│  Registry   │ ─── 記錄 Handoff (agent_handoffs table)
│ .dispatch() │     記錄 Activity Log (HANDOFF type)
└──────┬──────┘
       │
       │ handler.handle(payload)
       ▼
┌─────────────┐
│ Target Agent│ ─── 處理任務
│  .handle()  │     回傳結果
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  Registry   │ ─── 更新 Handoff 狀態 (completed/failed)
│ (callback)  │     記錄 Activity Log (TASK_END type)
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  intake.py  │ ─── 儲存 CEO Input (ceo_inputs table)
│ (response)  │     回傳結果給 Frontend
└─────────────┘
```

### 2.2 意圖路由表

| Intent | Agent | 說明 | 已實作 |
|--------|-------|------|--------|
| `product_feature` | PM | 產品功能需求 | Yes |
| `product_bug` | QA | 產品 Bug | No (Agent 未建立) |
| `opportunity` | HUNTER | 商機線索 | Yes |
| `project_status` | ORCHESTRATOR | 專案狀態查詢 | Yes |
| `project` | ORCHESTRATOR | 新專案需求 | Yes |
| `task` | ORCHESTRATOR | 任務 | Yes |
| `question` | KNOWLEDGE | 問題 | No (Agent 未建立) |
| `report` | DASHBOARD | 報告 | No (Agent 未建立) |
| `control` | SYSTEM | 控制指令 | No (Agent 未建立) |
| `info` | KNOWLEDGE | 資訊記錄 | No (Agent 未建立) |

### 2.3 Dispatch 狀態流

```
receive_ceo_input
  │
  ├── route_to in {PM, HUNTER, ORCHESTRATOR}?
  │     │
  │     ├── Yes → registry.dispatch() → 成功 → status = "dispatched"
  │     │                             → 失敗 → status = "awaiting_confirmation"
  │     │
  │     └── No → status = "awaiting_confirmation" or "processing"
  │
  ▼
confirm_input (CEO 確認)
  │
  ├── status != "dispatched"?
  │     │
  │     ├── Yes → registry.dispatch() → 實際派發
  │     └── No → 已派發，僅確認
  │
  ▼
  status = "confirmed"
```

---

## 3. 資料持久化策略

### 3.1 PostgreSQL（持久化狀態）

| Table | 用途 | 寫入時機 |
|-------|------|----------|
| `ceo_inputs` | CEO 輸入歷史 | intake.py receive_ceo_input |
| `ceo_todos` | CEO 待辦事項 | PM 建立 PRD 後 |
| `features` | 功能需求 | PM process_feature_request |
| `agent_handoffs` | Agent 互轉紀錄 | Registry dispatch |
| `activity_logs` | Agent 活動日誌 | 所有 Agent 操作 |
| `agents` | Agent 狀態 | base.py _update_db_status |
| `logs` | 行動日誌 | base.py _log_action, MessageBus |
| `ledger` | LLM 成本帳本 | base.py _record_llm_cost |
| `inbox` | CEO Inbox | MessageBus escalate_to_ceo |

### 3.2 Redis（訊息通訊）

| Channel Pattern | 用途 |
|-----------------|------|
| `agent:{id}:inbox` | Agent 收件匣（pub/sub） |
| `reply:{correlation_id}` | Query 回覆通道 |

### 3.3 連線設定

```bash
# PostgreSQL
DATABASE_URL=postgresql+asyncpg://nexus:nexus_dev@localhost:5432/nexus

# Redis
REDIS_URL=redis://localhost:6379/0
```

**Fallback**: Redis 不可用時系統仍可正常運作（Registry dispatch 不依賴 Redis）。

---

## 4. 新增 Agent Checklist

要新增一個 Agent（例如 `QA`），請按照以下步驟：

### Step 1: 建立 Agent 檔案

建立 `backend/app/agents/qa.py`：

```python
from typing import Any, Dict, List, Optional

class QAAgent:
    """QA Agent — 測試管理"""

    def __init__(self):
        self.id = "QA"
        self.name = "QA Agent"

    # --- AgentHandler Protocol ---

    @property
    def agent_id(self) -> str:
        return "QA"

    @property
    def agent_name(self) -> str:
        return "QA Agent"

    async def handle(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """AgentHandler 介面實作"""
        content = payload.get("content", "")
        entities = payload.get("entities", [])
        return await self.process_bug_report(content, entities)

    # --- 業務邏輯 ---

    async def process_bug_report(
        self, content: str, entities: List[Dict]
    ) -> Dict[str, Any]:
        """處理 Bug 回報"""
        # 實作業務邏輯...
        return {"status": "created", "bug_id": "BUG-001"}
```

**重點**：
- 實作 `agent_id` (property) — 回傳唯一 ID（如 `"QA"`）
- 實作 `agent_name` (property) — 回傳顯示名稱
- 實作 `handle(payload: Dict) -> Dict` — 接收 dispatch payload，回傳處理結果
- `handle()` 中從 payload 取出 content、entities、intent 等欄位
- 如果 entity 格式需要轉換（如 `entity_type` → `type`），在 `handle()` 中處理

### Step 2: 在 main.py 註冊

修改 `backend/app/main.py` lifespan：

```python
from app.agents.qa import QAAgent

# 在 registry 區塊中新增
registry.register(QAAgent())
```

### Step 3: 在 GATEKEEPER 路由表新增意圖

修改 `backend/app/agents/gatekeeper.py` 的 `_determine_route()`：

```python
routes = {
    ...
    Intent.PRODUCT_BUG: "QA",  # 確認已對應
    ...
}
```

如果需要新的意圖類型，也要修改 `Intent` enum。

### Step 4: （可選）新增 intake.py 可路由 Agent

如果希望 CEO 輸入能自動 dispatch 到新 Agent，修改 `backend/app/api/intake.py`：

```python
routable_agents = {"PM", "HUNTER", "ORCHESTRATOR", "QA"}  # 新增 QA
```

### Step 5: （可選）建立 API endpoint

建立 `backend/app/api/qa.py` 並在 `main.py` 中 `include_router`。

### Step 6: （可選）新增 DB Model

如果 Agent 需要自己的持久化資料，在 `backend/app/db/models.py` 新增 model。

---

## 5. Handoff 紀錄

### 5.1 Schema: `agent_handoffs`

| Column | Type | 說明 |
|--------|------|------|
| `id` | String(50) PK | Handoff ID（格式：`HO-XXXXXXXX`） |
| `from_agent` | String(50) | 來源 Agent（通常是 `GATEKEEPER`） |
| `to_agent` | String(50) | 目標 Agent |
| `intent` | String(50) | 意圖類型（nullable） |
| `payload` | JSON | 傳遞的資料 |
| `status` | String(20) | `dispatching` → `completed` / `failed` |
| `result` | JSON | Agent 處理結果（nullable） |
| `created_at` | DateTime | 建立時間 |
| `completed_at` | DateTime | 完成時間（nullable） |

### 5.2 常用查詢

```sql
-- 查看所有 Handoff 紀錄
SELECT id, from_agent, to_agent, intent, status, created_at
FROM agent_handoffs
ORDER BY created_at DESC;

-- 查看失敗的 Handoff
SELECT * FROM agent_handoffs WHERE status = 'failed';

-- 查看特定 Agent 接收的 Handoff
SELECT * FROM agent_handoffs WHERE to_agent = 'PM' ORDER BY created_at DESC;

-- 統計各 Agent 的 Handoff 數量
SELECT to_agent, status, COUNT(*) as count
FROM agent_handoffs
GROUP BY to_agent, status;

-- 查看完整的 Agent 活動鏈（Handoff + Activity Log）
SELECT
    h.id as handoff_id,
    h.from_agent,
    h.to_agent,
    h.intent,
    h.status,
    h.created_at,
    a.message,
    a.activity_type
FROM agent_handoffs h
LEFT JOIN activity_logs a ON a.metadata_json->>'handoff_id' = h.id
ORDER BY h.created_at DESC;
```

### 5.3 Activity Log 類型

| Type | 說明 | 觸發時機 |
|------|------|----------|
| `task_start` | 開始任務 | Agent 狀態變 working |
| `task_end` | 完成任務 | Agent 處理完 dispatch |
| `handoff` | 派發任務 | Registry dispatch 開始 |
| `status_change` | 狀態變更 | Agent 狀態變更 |
| `blocked` | 遭遇阻塞 | Agent 等待回覆或審核 |
| `unblocked` | 解除阻塞 | Agent 恢復執行 |
| `message` | 一般訊息 | CEO 輸入等 |
| `error` | 錯誤 | Agent 處理失敗 |
| `milestone` | 里程碑 | 重大事件 |

---

## 6. 基礎設施

### Docker Compose

```bash
# 啟動 PostgreSQL + Redis
docker-compose up -d

# 驗證
docker-compose ps
docker exec nexus-postgres psql -U nexus -c "SELECT 1"
docker exec nexus-redis redis-cli ping
```

### 後端啟動

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```

啟動時會看到：
```
   Redis connected: redis://localhost:6379/0
🚀 Nexus AI Company is starting up...
   Registered agents: ['GATEKEEPER', 'PM', 'HUNTER', 'ORCHESTRATOR']
```

---

## 附錄: 已完成的實作步驟

| Step | 內容 | Commit | Issue |
|------|------|--------|-------|
| 1 | Docker Compose 基礎設施 | `26b34b2` | #1 |
| 2 | 資料持久化遷移 (In-Memory → PostgreSQL) | `884dfef` | #2 |
| 3 | Agent Registry + Dispatcher | `c747edb` | #3 |
| 4 | Redis Message Bus | `663eaaf` | #4 |
| 5 | 設計文件 + Agent 新增指南 | — | #5 |
