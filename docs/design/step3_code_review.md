# Step 3: Agent Registry + Dispatcher — Code Review

**日期**: 2026-02-07
**審查範圍**: registry.py, gatekeeper.py, pm.py, hunter.py, orchestrator.py, intake.py, main.py, __init__.py
**結論**: 通過（修正 3 個問題後）

---

## 變更摘要

| 檔案 | 動作 | 說明 |
|------|------|------|
| `backend/app/agents/registry.py` | 新增 | AgentHandler Protocol + AgentRegistry + dispatch + get/set_registry |
| `backend/app/agents/gatekeeper.py` | 修改 | 新增 agent_id, agent_name properties + handle() 方法 |
| `backend/app/agents/pm.py` | 修改 | 新增 agent_id, agent_name properties + handle() 方法 |
| `backend/app/agents/hunter.py` | 修改 | 新增 agent_id, agent_name properties + handle() 方法（含 entity 格式轉換） |
| `backend/app/agents/orchestrator.py` | 修改 | 新增 agent_id, agent_name properties + handle() 方法 |
| `backend/app/api/intake.py` | 修改 | 硬編碼 PM dispatch → Registry dispatch；confirm_input 實作 |
| `backend/app/main.py` | 修改 | lifespan 中初始化 AgentRegistry 並註冊 4 個 Agent |
| `backend/app/agents/__init__.py` | 修改 | 導出 AgentRegistry, AgentHandler, get/set_registry |

---

## 審查結果

### 發現並修正的問題

| # | 問題 | 嚴重度 | 修正方式 |
|---|------|--------|----------|
| 1 | Entity 格式不一致 | High | HunterAgent.handle() 中加入 entity_type → type 轉換 |
| 2 | 雙重 dispatch | High | dispatch 成功後 status 改為 "dispatched"；confirm_input 檢查 status |
| 3 | Python 3.10+ union syntax | Low | `AgentRegistry \| None` → `Optional[AgentRegistry]` |

#### 問題 1: Entity 格式不一致

GATEKEEPER 的 `ParsedEntity` 使用 `entity_type` 欄位名，但 HunterAgent 的 `_extract_company()` 等方法使用 `entity.get("type")`。

**修正**: 在 `HunterAgent.handle()` 中將 `entity_type` 轉換為 `type`：
```python
entities = [
    {"type": e.get("entity_type", e.get("type")), "value": e.get("value"),
     "metadata": e.get("metadata", {})}
    for e in raw_entities
]
```

#### 問題 2: 雙重 dispatch

`receive_ceo_input` 會立即 dispatch，但 `confirm_input` 也會 dispatch，導致同一筆輸入被 dispatch 兩次。

**修正**:
- `receive_ceo_input`: dispatch 成功後 status 設為 `"dispatched"`（而非 `"awaiting_confirmation"`）
- `confirm_input`: 只在 `row.status != "dispatched"` 時才 dispatch

#### 問題 3: Python 版本相容

`_registry: AgentRegistry | None` 需要 Python 3.10+，而 codebase 其他地方使用 `Optional[T]`。

**修正**: 改為 `_registry: Optional[AgentRegistry] = None`

---

### PASS — 修正後全部通過

| 項目 | 說明 |
|------|------|
| AgentHandler Protocol | 使用 `@runtime_checkable` + `Protocol`，4 個 Agent 都正確實作 |
| Registry dispatch 流程 | record_handoff → activity_log → handle() → update_handoff → activity_log |
| Handoff DB 記錄 | 寫入 `agent_handoffs` table（Step 2 建立的 model） |
| Session 注入 | Registry 接收 `session_factory=AsyncSessionLocal`，與 Step 2 pattern 一致 |
| Agent 註冊 | main.py lifespan 中完成，啟動即可用 |
| 全域存取 | `get_registry()` / `set_registry()` 模式與 `get_activity_repo()` 一致 |
| 路由可擴充 | 新增 Agent 只需實作 Protocol + 在 main.py register |
| intake.py 解耦 | 不再直接 import PM agent，透過 registry.dispatch 間接呼叫 |
| confirm_input 實作 | 從 TODO → 實際查 DB + dispatch（不再回傳假資料） |
| 向後相容 | CEOInputResponse 格式不變，前端不受影響 |

---

## 設計決策記錄

1. **全域 Registry singleton**: 使用 `get_registry()` / `set_registry()` 函式模式（與 `get_activity_repo()` 一致），而非 request-scoped dependency injection。原因：Registry 生命週期是 application-wide，且 Agent 互相呼叫時不一定在 request context 中。

2. **handle() 中做格式轉換**: HunterAgent.handle() 負責將 dispatch payload 格式轉換為 `process_intake()` 所需格式。這保持了 `process_intake()` 的 API 不變，轉換邏輯集中在適配層。

3. **dispatch 狀態管理**: 用 `"dispatched"` 狀態區分已自動 dispatch 和 `"awaiting_confirmation"` 未 dispatch。避免 confirm_input 重複 dispatch。

4. **routable_agents 白名單**: intake.py 使用 `{"PM", "HUNTER", "ORCHESTRATOR"}` 白名單而非 `registry.get(target_id)` 判斷，確保只有業務上確定可處理的 Agent 才會被 dispatch。QA、KNOWLEDGE 等未實作的 Agent 不會被誤觸發。

---

## 不在 Step 3 範圍

| 項目 | 歸屬 |
|------|------|
| api/agents.py 從 MOCK_AGENTS 改用 Registry | 後續（需整合 Agent 狀態管理） |
| QA / DEVELOPER Agent 實作 | 後續 |
| Redis Message Bus | Step 4 |
