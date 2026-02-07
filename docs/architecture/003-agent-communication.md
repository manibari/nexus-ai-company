# 003: Agent 通訊機制

> **版本**: 2.0.0
> **日期**: 2026-02-07
> **變更**: asyncio Queue → Redis pub/sub MessageBus; 新增 AgentRegistry dispatch

---

## 設計目標

1. **Agent 間可互相查詢**：PM 可問 Sales 客戶資訊
2. **避免死鎖**：設計超時與回退機制
3. **可追溯**：所有通訊都記錄到 activity_logs 表
4. **支援阻擋機制**：區分內部阻擋與用戶阻擋
5. **持久化**：Redis pub/sub 確保重啟後訊息不遺失

---

## 實作架構

### AgentRegistry (registry.py)

統一管理所有 Agent 的註冊和派發。

```python
class AgentRegistry:
    """Agent 註冊中心"""

    def __init__(self):
        self._handlers: Dict[str, AgentHandler] = {}

    def register(self, handler: AgentHandler) -> None:
        self._handlers[handler.agent_id] = handler

    async def dispatch(self, agent_id: str, payload: Dict) -> Dict:
        handler = self._handlers.get(agent_id)
        if not handler:
            raise ValueError(f"Unknown agent: {agent_id}")
        return await handler.handle(payload)

    def list_agents(self) -> List[Dict]:
        return [
            {"id": h.agent_id, "name": h.agent_name}
            for h in self._handlers.values()
        ]
```

全域存取：`get_registry()` / `set_registry()`

### AgentHandler Protocol

所有 Agent 都遵循此介面：

```python
class AgentHandler(Protocol):
    @property
    def agent_id(self) -> str: ...

    @property
    def agent_name(self) -> str: ...

    async def handle(self, payload: Dict[str, Any]) -> Dict[str, Any]: ...
```

---

## Redis MessageBus (message_bus.py)

### Channel Pattern

```
agent:{agent_id}:inbox     — Agent 接收訊息的 channel
reply:{correlation_id}     — Request-Reply 模式的回覆 channel
broadcast:all              — 全體廣播 channel
```

### 核心 API

```python
class MessageBus:
    """Redis pub/sub 訊息匯流排"""

    def __init__(self, redis_client):
        self._redis = redis_client
        self._handlers: Dict[str, Callable] = {}

    def register_handler(self, agent_id: str, handler: Callable) -> None:
        """註冊 Agent 的訊息處理器"""
        self._handlers[agent_id] = handler

    async def send(self, to_agent: str, message: Dict) -> None:
        """發送訊息到指定 Agent（不等待回應）"""
        channel = f"agent:{to_agent}:inbox"
        await self._redis.publish(channel, json.dumps(message))

    async def request(
        self,
        to_agent: str,
        message: Dict,
        timeout: int = 30,
    ) -> Dict:
        """Request-Reply 模式：發送並等待回應"""
        correlation_id = str(uuid4())
        reply_channel = f"reply:{correlation_id}"
        message["correlation_id"] = correlation_id
        message["reply_channel"] = reply_channel

        # 訂閱回覆 channel
        pubsub = self._redis.pubsub()
        await pubsub.subscribe(reply_channel)

        # 發送
        await self.send(to_agent, message)

        # 等待回覆（含超時）
        try:
            async for msg in pubsub.listen():
                if msg["type"] == "message":
                    return json.loads(msg["data"])
        finally:
            await pubsub.unsubscribe(reply_channel)

    async def reply(self, correlation_id: str, response: Dict) -> None:
        """回覆 request"""
        channel = f"reply:{correlation_id}"
        await self._redis.publish(channel, json.dumps(response))
```

全域存取：`get_bus()` / `set_bus()`

---

## 派發流程

### 1. CEO 輸入 → Agent 處理

```
POST /api/v1/intake
        │
        ▼
  GATEKEEPER.handle(payload)
  → intent classification
  → route_to = "PM" / "HUNTER" / ...
        │
        ▼
  AgentRegistry.dispatch(route_to, payload)
        │
        ▼
  Target Agent.handle(payload) → result Dict
```

### 2. Agent 間查詢 (Redis pub/sub)

```
    PM                    Redis MessageBus              Sales/Hunter
    │                         │                            │
    │  send(to="HUNTER",     │                            │
    │    message={...})      │                            │
    │ ──────────────────────▶│  PUBLISH agent:HUNTER:inbox│
    │                        │ ──────────────────────────▶│
    │                        │                            │
    │  [BLOCKED_INTERNAL]    │                            │
    │                        │                            │
    │                        │  PUBLISH reply:{corr_id}   │
    │   response             │◀────────────────────────── │
    │◀───────────────────────│                            │
    │                        │                            │
    │  [UNBLOCKED]           │                            │
```

### 3. CEO Escalation

```
Agent 遇到需要 CEO 決策
        │
        ▼
  PM → _create_ceo_todo(feature)
        │
        ▼
  CeoTodo 寫入 PostgreSQL
  WebSocket 推送 inbox.new_item
        │
        ▼
  CEO 在前端審批 (approve/modify/reject)
        │
        ▼
  POST /api/v1/pm/features/{id}/decision
        │
        ▼
  PM.handle_ceo_decision()
  → Feature status 更新
  → ProductItem 建立 (if approve)
  → Activity Log 記錄
```

---

## 阻擋狀態處理

### Agent Base Class (base.py)

```python
class Agent:
    """Agent 基底類別 — Sense-Think-Act 循環"""

    async def sense(self) -> Dict:
        """從 DB 讀取當前狀態"""

    async def think(self, context: Dict) -> Dict:
        """LLM 分析 + 決策"""

    async def act(self, decision: Dict) -> Dict:
        """執行動作 + 寫入 DB"""

    # DB helper methods
    async def _record_llm_cost(self, ...): ...
    async def _log_activity(self, ...): ...
```

### 狀態類型

| 狀態 | 說明 | 觸發 |
|------|------|------|
| `idle` | 空閒 | 任務完成 |
| `working` | 執行中 | 接收到任務 |
| `blocked_internal` | 等待其他 Agent | query() 呼叫 |
| `blocked_user` | 等待 CEO 決策 | escalate_to_ceo() |

---

## 死鎖預防

- 所有 query 都有 timeout（預設 30s）
- MessageBus 支援 TTL，過期訊息自動清除
- 週期性檢查等待圖，發現循環則強制超時最早的等待者

---

## 參考文件

- [001-system-overview.md](./001-system-overview.md)
- [002-llm-abstraction.md](./002-llm-abstraction.md)
