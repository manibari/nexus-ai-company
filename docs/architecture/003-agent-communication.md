# 003: Agent 通訊機制

> **版本**: 1.0.0
> **日期**: 2026-02-06

---

## 設計目標

1. **Agent 間可互相查詢**：PM 可問 Sales 客戶資訊
2. **避免死鎖**：設計超時與回退機制
3. **可追溯**：所有通訊都記錄到 logs 表
4. **支援阻擋機制**：區分內部阻擋與用戶阻擋

---

## 通訊模型

### 訊息類型

```python
from enum import Enum
from dataclasses import dataclass
from typing import Optional, Any
from datetime import datetime


class MessageType(Enum):
    """訊息類型"""
    QUERY = "query"           # 查詢請求
    RESPONSE = "response"     # 查詢回應
    NOTIFY = "notify"         # 通知（不需回應）
    ESCALATE = "escalate"     # 升級給 CEO


class MessagePriority(Enum):
    """訊息優先級"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4  # 立即處理


@dataclass
class AgentMessage:
    """Agent 間的訊息"""
    id: str
    type: MessageType
    from_agent: str
    to_agent: str
    subject: str
    payload: dict
    priority: MessagePriority = MessagePriority.NORMAL
    correlation_id: Optional[str] = None  # 關聯原始訊息
    timeout_seconds: int = 30
    created_at: datetime = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()
```

---

## Message Bus 實作

```python
import asyncio
from collections import defaultdict
from typing import Callable, Dict, List
import logging

logger = logging.getLogger(__name__)


class MessageBus:
    """
    Agent 通訊中心

    特點：
    - 異步訊息傳遞
    - 支援 request-response 模式
    - 超時處理
    - 訊息持久化
    """

    def __init__(self, db_session):
        self.db = db_session
        self._handlers: Dict[str, Callable] = {}  # agent_id -> handler
        self._pending: Dict[str, asyncio.Future] = {}  # correlation_id -> future
        self._queue: Dict[str, asyncio.Queue] = defaultdict(asyncio.Queue)

    def register_agent(self, agent_id: str, handler: Callable):
        """註冊 Agent 的訊息處理器"""
        self._handlers[agent_id] = handler
        logger.info(f"Agent {agent_id} registered to message bus")

    async def send(self, message: AgentMessage) -> None:
        """
        發送訊息（不等待回應）

        用於 NOTIFY 類型的訊息
        """
        await self._persist_message(message)
        await self._queue[message.to_agent].put(message)

    async def query(
        self,
        message: AgentMessage,
        timeout: Optional[int] = None
    ) -> AgentMessage:
        """
        發送查詢並等待回應

        用於 QUERY 類型的訊息

        Raises:
            TimeoutError: 超過等待時間
            AgentUnavailableError: 目標 Agent 不可用
        """
        if message.type != MessageType.QUERY:
            raise ValueError("query() only accepts QUERY type messages")

        timeout = timeout or message.timeout_seconds

        # 建立 Future 等待回應
        future = asyncio.get_event_loop().create_future()
        self._pending[message.id] = future

        # 發送訊息
        await self._persist_message(message)
        await self._queue[message.to_agent].put(message)

        try:
            # 等待回應
            response = await asyncio.wait_for(future, timeout=timeout)
            return response
        except asyncio.TimeoutError:
            logger.warning(
                f"Query timeout: {message.from_agent} -> {message.to_agent}"
            )
            del self._pending[message.id]
            raise TimeoutError(
                f"No response from {message.to_agent} within {timeout}s"
            )

    async def respond(self, original: AgentMessage, payload: dict) -> None:
        """回應查詢"""
        response = AgentMessage(
            id=generate_id(),
            type=MessageType.RESPONSE,
            from_agent=original.to_agent,
            to_agent=original.from_agent,
            subject=f"RE: {original.subject}",
            payload=payload,
            correlation_id=original.id
        )

        await self._persist_message(response)

        # 解除等待
        if original.id in self._pending:
            self._pending[original.id].set_result(response)
            del self._pending[original.id]

    async def escalate_to_ceo(
        self,
        from_agent: str,
        subject: str,
        payload: dict,
        blocking: bool = True
    ) -> Optional[AgentMessage]:
        """
        升級給 CEO

        Args:
            from_agent: 發起升級的 Agent
            subject: 主題
            payload: 包含決策所需資訊
            blocking: 是否阻擋等待 CEO 回應

        Returns:
            CEO 的回應（如果 blocking=True）
        """
        message = AgentMessage(
            id=generate_id(),
            type=MessageType.ESCALATE,
            from_agent=from_agent,
            to_agent="CEO",
            subject=subject,
            payload=payload,
            priority=MessagePriority.URGENT
        )

        await self._persist_message(message)

        # 推送到前端 Inbox
        await self._push_to_inbox(message)

        if blocking:
            # 建立 Future 等待 CEO 回應
            future = asyncio.get_event_loop().create_future()
            self._pending[message.id] = future

            # 無限等待 CEO（但可被取消）
            response = await future
            return response

        return None

    async def _persist_message(self, message: AgentMessage):
        """持久化訊息到資料庫"""
        await self.db.execute(
            logs.insert().values(
                id=message.id,
                type=message.type.value,
                from_agent=message.from_agent,
                to_agent=message.to_agent,
                subject=message.subject,
                payload=json.dumps(message.payload),
                correlation_id=message.correlation_id,
                created_at=message.created_at
            )
        )

    async def _push_to_inbox(self, message: AgentMessage):
        """推送訊息到 CEO 前端 Inbox"""
        # 透過 WebSocket 推送
        await websocket_manager.broadcast({
            "event": "inbox.new_item",
            "data": {
                "id": message.id,
                "from": message.from_agent,
                "subject": message.subject,
                "payload": message.payload,
                "priority": message.priority.value,
                "created_at": message.created_at.isoformat()
            }
        })
```

---

## 阻擋狀態處理

```python
class BlockingStatus(Enum):
    """阻擋狀態"""
    NONE = "none"                    # 正常運作
    BLOCKED_INTERNAL = "internal"   # 等待其他 Agent 回應
    BLOCKED_USER = "user"           # 等待 CEO 決策


@dataclass
class BlockingContext:
    """阻擋上下文"""
    status: BlockingStatus
    waiting_for: str  # Agent ID 或 "CEO"
    reason: str
    message_id: str
    started_at: datetime


class Agent:
    """Agent 基底類別中的阻擋處理"""

    def __init__(self, agent_id: str, message_bus: MessageBus):
        self.id = agent_id
        self.bus = message_bus
        self.blocking: Optional[BlockingContext] = None

    async def query_agent(
        self,
        target: str,
        subject: str,
        payload: dict
    ) -> dict:
        """
        查詢其他 Agent

        自動處理阻擋狀態
        """
        message = AgentMessage(
            id=generate_id(),
            type=MessageType.QUERY,
            from_agent=self.id,
            to_agent=target,
            subject=subject,
            payload=payload
        )

        # 進入內部阻擋狀態
        self.blocking = BlockingContext(
            status=BlockingStatus.BLOCKED_INTERNAL,
            waiting_for=target,
            reason=subject,
            message_id=message.id,
            started_at=datetime.utcnow()
        )
        await self._update_status()

        try:
            response = await self.bus.query(message)
            return response.payload
        finally:
            # 解除阻擋
            self.blocking = None
            await self._update_status()

    async def request_ceo_approval(
        self,
        subject: str,
        options: List[dict],
        context: dict
    ) -> dict:
        """
        請求 CEO 審批

        Args:
            subject: 審批主題
            options: 可選項目（如折扣選項）
            context: 背景資訊

        Returns:
            CEO 的決策
        """
        payload = {
            "options": options,
            "context": context,
            "requested_at": datetime.utcnow().isoformat()
        }

        # 進入用戶阻擋狀態
        message_id = generate_id()
        self.blocking = BlockingContext(
            status=BlockingStatus.BLOCKED_USER,
            waiting_for="CEO",
            reason=subject,
            message_id=message_id,
            started_at=datetime.utcnow()
        )
        await self._update_status()

        try:
            response = await self.bus.escalate_to_ceo(
                from_agent=self.id,
                subject=subject,
                payload=payload,
                blocking=True
            )
            return response.payload
        finally:
            self.blocking = None
            await self._update_status()

    async def _update_status(self):
        """更新 Agent 狀態到資料庫"""
        status = "idle"
        if self.blocking:
            status = f"blocked_{self.blocking.status.value}"

        await self.db.execute(
            agents.update()
            .where(agents.c.id == self.id)
            .values(
                status=status,
                blocking_info=json.dumps(asdict(self.blocking)) if self.blocking else None
            )
        )
```

---

## 死鎖預防

```python
class DeadlockDetector:
    """死鎖偵測器"""

    def __init__(self, message_bus: MessageBus):
        self.bus = message_bus

    async def check_deadlock(self) -> List[str]:
        """
        檢查是否存在循環等待

        Returns:
            參與死鎖的 Agent ID 列表（空表示無死鎖）
        """
        # 建立等待圖
        wait_graph = {}
        for agent_id, handler in self.bus._handlers.items():
            agent = handler.agent  # 假設 handler 有 agent 引用
            if agent.blocking and agent.blocking.status == BlockingStatus.BLOCKED_INTERNAL:
                wait_graph[agent_id] = agent.blocking.waiting_for

        # DFS 檢測循環
        visited = set()
        rec_stack = set()

        def dfs(node, path):
            if node in rec_stack:
                # 找到循環
                cycle_start = path.index(node)
                return path[cycle_start:]
            if node in visited:
                return []

            visited.add(node)
            rec_stack.add(node)
            path.append(node)

            if node in wait_graph:
                result = dfs(wait_graph[node], path)
                if result:
                    return result

            path.pop()
            rec_stack.remove(node)
            return []

        for node in wait_graph:
            result = dfs(node, [])
            if result:
                return result

        return []

    async def resolve_deadlock(self, agents: List[str]):
        """
        解決死鎖

        策略：強制超時最早開始等待的 Agent
        """
        # 找出最早開始等待的 Agent
        earliest = None
        earliest_time = None

        for agent_id in agents:
            agent = self.bus._handlers[agent_id].agent
            if earliest_time is None or agent.blocking.started_at < earliest_time:
                earliest = agent_id
                earliest_time = agent.blocking.started_at

        # 強制超時
        logger.warning(f"Resolving deadlock by timing out {earliest}")
        if earliest in self.bus._pending:
            self.bus._pending[earliest].set_exception(
                TimeoutError("Forced timeout due to deadlock")
            )
```

---

## 序列圖範例

### PM 向 Sales 查詢客戶資訊

```
    PM                    MessageBus                 Sales
    │                         │                        │
    │  query(customer_info)   │                        │
    │ ──────────────────────▶ │                        │
    │                         │   deliver message      │
    │                         │ ─────────────────────▶ │
    │                         │                        │
    │  [BLOCKED_INTERNAL]     │                        │
    │                         │                        │
    │                         │      respond()         │
    │                         │ ◀───────────────────── │
    │   response              │                        │
    │ ◀────────────────────── │                        │
    │                         │                        │
    │  [UNBLOCKED]            │                        │
```

---

## 參考文件

- [001-system-overview.md](./001-system-overview.md)
- [002-llm-abstraction.md](./002-llm-abstraction.md)
