# Step 4: Redis Message Bus — Code Review

**日期**: 2026-02-07
**審查範圍**: message_bus.py, base.py, main.py
**結論**: 通過（修正 1 個問題後）

---

## 變更摘要

| 檔案 | 動作 | 說明 |
|------|------|------|
| `backend/app/agents/message_bus.py` | 新增 | MessageBus class：send, query, reply, escalate_to_ceo, start/stop_listening |
| `backend/app/agents/base.py` | 修改 | 實作 3 個 TODO：_update_db_status, _log_action, _record_llm_cost；修正 _request_approval |
| `backend/app/main.py` | 修改 | lifespan 中初始化 Redis + MessageBus，graceful fallback |

---

## 審查結果

### 發現並修正的問題

| # | 問題 | 嚴重度 | 修正方式 |
|---|------|--------|----------|
| 1 | `_request_approval` 型別錯誤 | High | `response.payload.get(...)` → `response.get(...)` |

#### 問題 1: _request_approval 型別不匹配

`escalate_to_ceo()` 回傳 `Dict[str, Any]`，但 `_request_approval` 用 `response.payload.get("approved", False)` 存取。`payload` 是 Dict 沒有的屬性，會觸發 `AttributeError`。

**修正**: `response.payload.get(...)` → `response.get("approved", False)`

---

### PASS — 修正後全部通過

| 項目 | 說明 |
|------|------|
| MessageBus 三種通訊模式 | send (fire-and-forget), query (request-reply), escalate_to_ceo (CEO 審核) |
| Redis channel 命名 | `agent:{id}:inbox` 用於收件，`reply:{correlation_id}` 用於 query 回覆 |
| BusMessage 資料結構 | id, from/to_agent, subject, payload, reply_to, timestamp |
| 訊息持久化 | 每條訊息寫入 `logs` table（type=notification/query/reply） |
| escalate_to_ceo | 寫入 `inbox` table + activity_log，支援 blocking/non-blocking |
| _update_db_status | 寫入/更新 `agents` table，upsert pattern（不存在則建立） |
| _log_action | 寫入 `logs` table，記錄 action + params + reasoning + result |
| _record_llm_cost | 寫入 `ledger` table，使用 getattr 安全存取 response 屬性 |
| Redis graceful fallback | Redis 不可用時不影響系統啟動，僅 MessageBus 停用 |
| Shutdown cleanup | `redis_client.aclose()` 正確清理連線 |
| 全域存取 | `get_bus()` / `set_bus()` 與 Registry 模式一致 |

---

## 設計決策記錄

1. **Redis optional**: Redis 不可用時系統仍可運作（Registry dispatch 不依賴 Redis）。MessageBus 是額外的非同步通訊層，為未來長時間任務準備。

2. **Pub/Sub + Request-Reply**: query() 使用 Redis pub/sub 的 reply channel pattern 實作同步查詢。發送者先訂閱 reply channel，再 publish 到目標 channel。接收者處理後 publish 到 reply channel。

3. **start_listening 非自動啟動**: MessageBus 不自動啟動監聽，需要手動呼叫 `start_listening()`（通常在 background task 中）。原因：目前 Agent 主要透過 Registry dispatch 同步呼叫，Message Bus 的監聽機制是為未來 Agent autonomous loop 準備。

4. **base.py 的 DB 操作全部 try/except**: 三個 TODO 方法都用 try/except 包裝，失敗僅 log 不影響主流程。原因：DB 記錄是輔助功能，不應影響 Agent 的核心 Sense-Think-Act cycle。

---

## 不在 Step 4 範圍

| 項目 | 歸屬 |
|------|------|
| start_listening background task | 後續（需要 Agent autonomous loop） |
| base.py Agent 子類實作 | 後續（目前的 Agent 用獨立 class） |
| Redis 訊息過期 / TTL | 後續優化 |
