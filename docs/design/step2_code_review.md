# Step 2: 資料持久化遷移 — Code Review

**日期**: 2026-02-07
**審查範圍**: models.py, repository.py, pm.py, activity_log.py, intake.py, ceo_todo.py, activity.py
**結論**: 全部通過，可以 commit

---

## 變更摘要

| 檔案 | 動作 | 說明 |
|------|------|------|
| `backend/app/db/models.py` | 修改 | 新增 CeoTodo, Feature, CeoInput, AgentHandoff, ActivityLog 5 個 model |
| `backend/app/ceo/repository.py` | 重寫 | TodoRepository: in-memory dict → SQLAlchemy CRUD |
| `backend/app/agents/pm.py` | 修改 | FeatureRepository: in-memory dict → SQLAlchemy CRUD |
| `backend/app/agents/activity_log.py` | 重寫 | 從 raw sqlite3 → SQLAlchemy async，新增 HANDOFF ActivityType |
| `backend/app/api/intake.py` | 修改 | CEO 輸入存入 ceo_inputs table，實作 list/get/pending/summary endpoints |
| `backend/app/api/ceo_todo.py` | 修改 | `_repo` → `_get_repo()` lazy init with AsyncSessionLocal |
| `backend/app/api/activity.py` | 修改 | `get_stats()` → `await get_stats()` |

---

## 審查結果

### PASS — 全部通過

| 項目 | 說明 |
|------|------|
| DB Models 完整性 | 5 個新 model 都有正確的 column type、index、nullable 設定 |
| Repository API 相容性 | TodoRepository 和 FeatureRepository 保持完全相同的 public API |
| Session 注入 | 全部使用 `session_factory=AsyncSessionLocal` lazy init，避免模組載入時連線 |
| 循環引用 | PM 的 `_get_todo_repo` 正確使用 `from app.api.ceo_todo import _get_repo`（函式引用，非變數） |
| Async 一致性 | `activity.py` 的 `get_stats()` 已改為 `await`；所有 DB 操作都是 async |
| 舊 sqlite3 移除 | `activity_log.py` 不再 import sqlite3，完全使用 SQLAlchemy |
| 新 ActivityType | 新增 `HANDOFF = "handoff"` 為 Step 3 準備 |
| Intake 持久化 | `receive_ceo_input` 結束前存入 `ceo_inputs` table，失敗不影響回傳 |
| TODO endpoints 實作 | `list_ceo_inputs`, `get_ceo_input`, `list_pending_confirmations`, `get_intake_summary` 全部實作 |

### 設計決策記錄

1. **Domain model 與 DB model 分離**: TodoItem (dataclass) 和 CeoTodo (SQLAlchemy) 分離，透過 `_domain_to_db` / `_db_to_domain` 轉換。保持 API 層不受 ORM 影響。

2. **Lazy init pattern**: 所有 repository 都使用 `_get_repo()` 函式而非模組層級變數初始化，確保 DB engine 在使用時才建立 session。

3. **自帶 session 管理**: 每個 repository method 都 `async with self._session()` 開新 session，而非共用 request-scoped session。簡化了不在 API request context 中呼叫的情境（如 Agent 間互相呼叫）。

---

## 已知但不在 Step 2 範圍

| 項目 | 歸屬 |
|------|------|
| AgentHandoff 實際寫入 | Step 3 (Registry dispatch 會寫入) |
| `confirm_input` endpoint 實際邏輯 | Step 3 (需要 Registry dispatch) |
| 現有 SQLite data 遷移 | 不在範圍（少量測試資料，可重新產生） |
