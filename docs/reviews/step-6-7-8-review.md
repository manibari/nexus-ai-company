# Code Review: Step 6-7-8

> Feature → ProductItem Bridge + ProductRepository PostgreSQL + 架構文件更新
> Date: 2026-02-07
> Issues: #6, #7, #8

---

## 變更摘要

### Issue #6: Feature → ProductItem Bridge
**問題**: PM Agent 的 `_assign_to_developer()` 只建立 task dict，沒有建立 `ProductItem`。Product Board 永遠是空的。

**修改**:
1. `product/repository.py` — 新增 `get_product_repo()` / `set_product_repo()` 全域存取器
2. `product/__init__.py` — 新增 exports
3. `api/product.py` — `_repo = ProductRepository()` → `get_product_repo()` (lazy init)
4. `agents/pm.py` — `_assign_to_developer()` 末尾新增 `_create_product_item()`:
   - Feature 欄位對應 → ProductItem 欄位
   - `stage = spec_ready` (PRD 已完成，跳過 backlog)
   - Activity Log MILESTONE 記錄

### Issue #7: ProductRepository PostgreSQL 遷移
**問題**: `ProductRepository` 是 in-memory dict，重啟歸零。

**修改**:
1. `db/models.py` — 新增 `ProductItemDB` ORM model (所有 ProductItem 欄位)
2. `product/repository.py` — 全面改寫:
   - `__init__(session_factory)` 接受 session factory
   - `_domain_to_db()` / `_db_to_domain()` 轉換函數 (QA/UAT → JSON 序列化)
   - 所有 CRUD 方法使用 `async with self._session()` + SQLAlchemy
   - `get_dashboard()` / `get_roadmap()` / `get_statistics()` 改為 async
   - `get_product_repo()` 自動注入 `AsyncSessionLocal`
3. `api/product.py` — dashboard/roadmap/statistics 加 `await`

### Issue #8: 架構文件更新
**問題**: 文件仍描述 SQLite + asyncio Queue。

**修改**:
1. `001-system-overview.md`:
   - DATABASE: SQLite → PostgreSQL + Redis
   - Agent Orchestrator → AgentRegistry + dispatch()
   - Tables: 列出全部 10 tables
   - 新增 Feature → Product Board 流程圖
2. `003-agent-communication.md`:
   - Message Bus: asyncio Queue → Redis pub/sub
   - Channel pattern: `agent:{id}:inbox`, `reply:{correlation_id}`
   - 新增 AgentHandler Protocol 說明
   - 更新序列圖

---

## 修改檔案清單

| 檔案 | 動作 | Issue |
|------|------|-------|
| `backend/app/product/repository.py` | 重寫 | #6, #7 |
| `backend/app/product/__init__.py` | 修改 | #6 |
| `backend/app/api/product.py` | 修改 | #6, #7 |
| `backend/app/agents/pm.py` | 修改 | #6 |
| `backend/app/db/models.py` | 修改 | #7 |
| `docs/architecture/001-system-overview.md` | 重寫 | #8 |
| `docs/architecture/003-agent-communication.md` | 重寫 | #8 |

---

## 架構一致性檢查

| Pattern | 符合? | 說明 |
|---------|-------|------|
| Lazy init | YES | `get_product_repo()` 延遲建立 + 注入 AsyncSessionLocal |
| Domain ↔ DB 分離 | YES | `_domain_to_db()` / `_db_to_domain()` 轉換 |
| Session-per-operation | YES | 每個 repo 方法 `async with self._session()` |
| Global singleton | YES | `get_product_repo()` / `set_product_repo()` |
| AgentHandler Protocol | YES | PM.handle() → _assign_to_developer() → _create_product_item() |

---

## 風險評估

| 風險 | 等級 | 緩解 |
|------|------|------|
| QA/UAT JSON 反序列化 | Low | `_db_to_domain()` 有 fallback defaults |
| ProductItem ID 碰撞 | Very Low | UUID hex[:4] + year prefix |
| `get_product_repo()` thread safety | Low | FastAPI single-threaded event loop |
| 大量 ProductItem 的 dashboard 效能 | Medium | `list(limit=10000)` 上限，未來可改 SQL aggregation |

---

## 語法檢查

```
OK  backend/app/product/repository.py
OK  backend/app/api/product.py
OK  backend/app/agents/pm.py
OK  backend/app/db/models.py
OK  backend/app/product/__init__.py
All files pass syntax check
```
