# Step 9-10 Code Review: Agent API 整合 + 前端 UI 同步

## Issue #9: Agent API 整合 — MOCK_AGENTS → Registry

### 修改檔案
| 檔案 | 動作 | 說明 |
|------|------|------|
| `backend/app/api/agents.py` | 修改 | MOCK_AGENTS → Registry + AGENT_ROLES |

### 變更摘要

1. **移除 `MOCK_AGENTS` 列表** — 不再硬編碼 Agent 資料
2. **新增 `AGENT_ROLES` dict** — 定義 7 個 Agent 的角色名稱（CEO, GATEKEEPER, PM, HUNTER, DEVELOPER, QA, ORCHESTRATOR）
3. **新增 `_agent_states` dict** — Runtime 狀態快取，記錄每個 Agent 的即時狀態
4. **`list_agents()` 改用 Registry** — 從 `get_registry().list_agents()` 取得已註冊 Agent 名稱，合併 `AGENT_ROLES` 產生完整列表
5. **`get_agent()` 改用 `AGENT_ROLES`** — 以 `AGENT_ROLES` 為有效 Agent ID 清單，透過 `_get_agent_status()` 取得狀態
6. **`update_agent_status()` 改用 `_agent_states`** — 不再遍歷 MOCK list，直接查表更新。Activity Log 記錄邏輯不變

### 設計決策

- **為何保留 `AGENT_ROLES` 而不完全依賴 Registry？**
  - CEO、DEVELOPER、QA 等 Agent 尚未實作 `AgentHandler`，不會出現在 Registry 中
  - 前端需要看到全部 7 個 Agent，即使部分尚未註冊
  - `AGENT_ROLES` 作為「期望存在的 Agent」白名單

- **`_agent_states` 生命週期**
  - Module-level dict，app 重啟時重置
  - 首次查詢時 lazy init，從 Registry 取得名稱
  - 後續 PUT 更新直接修改快取物件

---

## Issue #10: 前端 UI 同步 + PM API + 設計文件

### 修改檔案
| 檔案 | 動作 | 說明 |
|------|------|------|
| `backend/app/api/pm.py` | 新增 | PM Agent REST API endpoints |
| `frontend/src/components/CEOInbox.tsx` | 修改 | Input Queue UI + 指令歷史 |
| `frontend/src/components/OfficeMap.tsx` | 修改 | Agent 名稱 + 房間更新 |
| `docs/design/ceo_intake_intent_classification.md` | 新增 | 意圖分類設計文件 |

### 各檔案說明

#### `backend/app/api/pm.py` (新增, 157 行)
- `POST /features` — 建立功能需求
- `GET /features` — 列出功能需求（支援 project/status filter）
- `GET /features/{id}` — 功能需求詳情
- `POST /features/{id}/decision` — CEO 決策 (approve/modify/reject)
- `GET /stats` — PM 統計（by status/project/priority）
- `GET /health` — 健康檢查
- 已在 `main.py` L107 註冊: `app.include_router(pm.router, prefix="/api/v1/pm")`

#### `frontend/src/components/CEOInbox.tsx` (修改, 711 行)
- 新增 `InputQueueItem` interface
- 新增 Input 分頁（Tab: To-Do | Input）
- `handleInputSubmit()` 送出後加入 `inputQueue` + 顯示 intent/confidence
- `handleInputAction()` 確認/取消 input
- 指令歷史列表（intent badge, agent chain, summary, suggested_actions）

#### `frontend/src/components/OfficeMap.tsx` (修改, 312 行)
- ROOMS: CEO Office 加入 CEO agent, Finance→Product (PM)
- AGENT_COLORS: BUILDER→DEVELOPER, INSPECTOR→QA, LEDGER→PM, 新增 CEO
- 全部 7 個 Agent 正確分配到對應房間

#### `docs/design/ceo_intake_intent_classification.md` (新增, 220 行)
- CEO Intake 意圖分類完整設計文件
- IntentType 定義（7 種意圖）
- Entity Extraction 規格
- Agent 工作流程圖（Feature/Opportunity/Bug 三條路徑）
- GATEKEEPER Gemini Prompt 範例
- PM Agent / QA Agent 規格

---

## 驗證清單

- [ ] `GET /api/v1/agents/` → 回傳 7 個 Agent（含 Registry 名稱）
- [ ] `GET /api/v1/agents/PM` → 正確回傳 PM Agent 資訊
- [ ] `PUT /api/v1/agents/PM/status` → 更新狀態 + Activity Log 記錄
- [ ] `GET /api/v1/pm/health` → PM Agent healthy
- [ ] `GET /api/v1/pm/features` → 列出 features
- [ ] OfficeMap 前端 → 7 個 Agent 在正確房間
- [ ] CEOInbox Input tab → 可送出指令 + 看到 intent 分析結果
