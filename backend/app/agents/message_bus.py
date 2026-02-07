"""
Redis Message Bus

Agent 間非同步通訊機制：
- send(): 單向通知（publish to Redis channel）
- query(): 同步查詢（request-reply pattern via Redis）
- escalate_to_ceo(): 升級到 CEO（建立 Todo / Inbox item）
"""

import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional
from uuid import uuid4

logger = logging.getLogger(__name__)


@dataclass
class BusMessage:
    """Message Bus 訊息格式"""
    id: str
    from_agent: str
    to_agent: str
    subject: str
    payload: Dict[str, Any]
    reply_to: Optional[str] = None  # reply channel for query pattern
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.utcnow().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "from_agent": self.from_agent,
            "to_agent": self.to_agent,
            "subject": self.subject,
            "payload": self.payload,
            "reply_to": self.reply_to,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BusMessage":
        return cls(
            id=data["id"],
            from_agent=data["from_agent"],
            to_agent=data["to_agent"],
            subject=data["subject"],
            payload=data.get("payload", {}),
            reply_to=data.get("reply_to"),
            timestamp=data.get("timestamp", ""),
        )


class MessageBus:
    """
    Redis-based Message Bus

    提供 Agent 間通訊的三種模式：
    1. send (fire-and-forget): 發送通知到 Redis channel
    2. query (request-reply): 發送請求並等待回覆
    3. escalate_to_ceo: 建立 CEO Inbox item 等待決策

    Channel 命名規則:
    - agent:{agent_id}:inbox  — Agent 的收件匣
    - reply:{correlation_id}  — query 的回覆通道
    """

    CHANNEL_PREFIX = "agent"
    REPLY_PREFIX = "reply"

    def __init__(self, redis_client, registry=None, session_factory=None):
        """
        Args:
            redis_client: redis.asyncio.Redis instance
            registry: AgentRegistry（用於查詢 Agent 是否存在）
            session_factory: AsyncSessionLocal（用於 DB 寫入）
        """
        self.redis = redis_client
        self.registry = registry
        self._session_factory = session_factory
        self._handlers: Dict[str, Callable] = {}
        self._running = False

    def _channel_for(self, agent_id: str) -> str:
        """取得 Agent 的 channel 名稱"""
        return f"{self.CHANNEL_PREFIX}:{agent_id}:inbox"

    def _reply_channel(self, correlation_id: str) -> str:
        """取得回覆 channel 名稱"""
        return f"{self.REPLY_PREFIX}:{correlation_id}"

    # === 核心通訊方法 ===

    async def send(
        self,
        target: str,
        subject: str,
        payload: Dict[str, Any],
        from_agent: str = "SYSTEM",
    ):
        """
        單向通知（fire-and-forget）

        發送訊息到目標 Agent 的 Redis channel。
        不等待回覆。

        Args:
            target: 目標 Agent ID
            subject: 訊息主題
            payload: 訊息內容
            from_agent: 發送者 Agent ID
        """
        msg = BusMessage(
            id=f"MSG-{uuid4().hex[:8].upper()}",
            from_agent=from_agent,
            to_agent=target,
            subject=subject,
            payload=payload,
        )

        channel = self._channel_for(target)
        await self.redis.publish(channel, json.dumps(msg.to_dict()))

        # 同時寫入 Log DB
        await self._log_message(msg, msg_type="notification")

        logger.info(f"[MessageBus] {from_agent} → {target}: {subject}")

    async def query(
        self,
        target: str,
        subject: str,
        payload: Dict[str, Any],
        from_agent: str = "SYSTEM",
        timeout: int = 30,
    ) -> Dict[str, Any]:
        """
        同步查詢（request-reply pattern）

        發送請求到目標 Agent，等待回覆。
        使用 Redis pub/sub 的 reply channel 實作。

        Args:
            target: 目標 Agent ID
            subject: 查詢主題
            payload: 查詢內容
            from_agent: 發送者 Agent ID
            timeout: 超時秒數

        Returns:
            回覆的 payload

        Raises:
            TimeoutError: 超時未收到回覆
        """
        correlation_id = uuid4().hex[:12]
        reply_channel = self._reply_channel(correlation_id)

        msg = BusMessage(
            id=f"QRY-{uuid4().hex[:8].upper()}",
            from_agent=from_agent,
            to_agent=target,
            subject=subject,
            payload=payload,
            reply_to=reply_channel,
        )

        # 先訂閱 reply channel
        pubsub = self.redis.pubsub()
        await pubsub.subscribe(reply_channel)

        try:
            # 發送查詢
            channel = self._channel_for(target)
            await self.redis.publish(channel, json.dumps(msg.to_dict()))
            await self._log_message(msg, msg_type="query")

            logger.info(f"[MessageBus] Query {from_agent} → {target}: {subject}")

            # 等待回覆
            deadline = asyncio.get_event_loop().time() + timeout
            while asyncio.get_event_loop().time() < deadline:
                raw = await pubsub.get_message(
                    ignore_subscribe_messages=True,
                    timeout=1.0,
                )
                if raw and raw["type"] == "message":
                    reply_data = json.loads(raw["data"])
                    reply_msg = BusMessage.from_dict(reply_data)
                    await self._log_message(reply_msg, msg_type="reply")
                    return reply_msg.payload

            raise TimeoutError(
                f"Query to {target} timed out after {timeout}s"
            )

        finally:
            await pubsub.unsubscribe(reply_channel)
            await pubsub.aclose()

    async def reply(
        self,
        original_msg: BusMessage,
        payload: Dict[str, Any],
        from_agent: str = "SYSTEM",
    ):
        """
        回覆 query 請求

        Args:
            original_msg: 原始查詢訊息（需含 reply_to）
            payload: 回覆內容
            from_agent: 回覆者 Agent ID
        """
        if not original_msg.reply_to:
            logger.warning(f"Cannot reply: message {original_msg.id} has no reply_to")
            return

        reply_msg = BusMessage(
            id=f"RPL-{uuid4().hex[:8].upper()}",
            from_agent=from_agent,
            to_agent=original_msg.from_agent,
            subject=f"RE: {original_msg.subject}",
            payload=payload,
        )

        await self.redis.publish(original_msg.reply_to, json.dumps(reply_msg.to_dict()))
        logger.info(f"[MessageBus] Reply {from_agent} → {original_msg.from_agent}")

    async def escalate_to_ceo(
        self,
        from_agent: str,
        subject: str,
        payload: Dict[str, Any],
        blocking: bool = True,
    ) -> Dict[str, Any]:
        """
        升級到 CEO

        建立 CEO Inbox item，等待 CEO 決策。

        Args:
            from_agent: 來源 Agent ID
            subject: 議題主題
            payload: 議題內容
            blocking: 是否阻塞等待 CEO 回覆

        Returns:
            CEO 的決策結果（如果 blocking=True），否則回傳 inbox item info
        """
        inbox_id = f"INB-{uuid4().hex[:8].upper()}"

        # 寫入 DB (inbox table)
        if self._session_factory:
            try:
                from app.db.models import InboxItem
                async with self._session_factory() as session:
                    item = InboxItem(
                        id=inbox_id,
                        from_agent=from_agent,
                        subject=subject,
                        payload=payload,
                        priority=payload.get("priority", 2),
                        status="pending",
                        created_at=datetime.utcnow(),
                    )
                    session.add(item)
                    await session.commit()
            except Exception as e:
                logger.error(f"Failed to create inbox item: {e}")

        # 記錄活動
        from app.agents.activity_log import ActivityType, get_activity_repo
        activity_repo = get_activity_repo()
        await activity_repo.log(
            agent_id=from_agent,
            agent_name=from_agent,
            activity_type=ActivityType.BLOCKED,
            message=f"升級到 CEO: {subject}",
            metadata={"inbox_id": inbox_id, "payload": payload},
        )

        logger.info(f"[MessageBus] Escalation from {from_agent}: {subject}")

        if blocking:
            # 等待 CEO 回覆（透過 Redis channel）
            reply_channel = self._reply_channel(inbox_id)
            pubsub = self.redis.pubsub()
            await pubsub.subscribe(reply_channel)

            try:
                # 長等待（CEO 可能需要時間）— 10 分鐘
                timeout = 600
                deadline = asyncio.get_event_loop().time() + timeout
                while asyncio.get_event_loop().time() < deadline:
                    raw = await pubsub.get_message(
                        ignore_subscribe_messages=True,
                        timeout=2.0,
                    )
                    if raw and raw["type"] == "message":
                        reply_data = json.loads(raw["data"])
                        return BusMessage.from_dict(reply_data).payload

                # 超時：回傳 pending 狀態讓 caller 決定下一步
                return {
                    "status": "timeout",
                    "inbox_id": inbox_id,
                    "message": "CEO 尚未回覆",
                }
            finally:
                await pubsub.unsubscribe(reply_channel)
                await pubsub.aclose()
        else:
            return {
                "status": "pending",
                "inbox_id": inbox_id,
                "message": "已提交 CEO 審核",
            }

    # === 訊息訂閱 ===

    def register_handler(self, agent_id: str, handler: Callable):
        """
        註冊 Agent 的訊息處理器

        Args:
            agent_id: Agent ID
            handler: async callable(BusMessage) -> Dict
        """
        self._handlers[agent_id] = handler
        logger.info(f"[MessageBus] Registered handler for {agent_id}")

    async def start_listening(self):
        """開始監聽所有已註冊 Agent 的 channel"""
        if not self._handlers:
            logger.info("[MessageBus] No handlers registered, skip listening")
            return

        self._running = True
        channels = [self._channel_for(agent_id) for agent_id in self._handlers]

        pubsub = self.redis.pubsub()
        await pubsub.subscribe(*channels)

        logger.info(f"[MessageBus] Listening on {len(channels)} channels")

        try:
            while self._running:
                raw = await pubsub.get_message(
                    ignore_subscribe_messages=True,
                    timeout=1.0,
                )
                if raw and raw["type"] == "message":
                    try:
                        msg = BusMessage.from_dict(json.loads(raw["data"]))
                        handler = self._handlers.get(msg.to_agent)
                        if handler:
                            result = await handler(msg)
                            # 如果有 reply_to，自動回覆
                            if msg.reply_to and result:
                                await self.reply(msg, result, from_agent=msg.to_agent)
                    except Exception as e:
                        logger.error(f"[MessageBus] Error handling message: {e}")
        finally:
            await pubsub.unsubscribe(*channels)
            await pubsub.aclose()

    async def stop_listening(self):
        """停止監聽"""
        self._running = False

    # === DB 記錄 ===

    async def _log_message(self, msg: BusMessage, msg_type: str = "message"):
        """記錄訊息到 logs table"""
        if not self._session_factory:
            return
        try:
            from app.db.models import Log
            async with self._session_factory() as session:
                log = Log(
                    id=msg.id,
                    type=msg_type,
                    agent_id=msg.from_agent,
                    from_agent=msg.from_agent,
                    to_agent=msg.to_agent,
                    subject=msg.subject,
                    payload=msg.payload,
                    correlation_id=msg.reply_to,
                    created_at=datetime.utcnow(),
                )
                session.add(log)
                await session.commit()
        except Exception as e:
            logger.error(f"Failed to log message: {e}")

    # === 工具方法 ===

    async def ping(self) -> bool:
        """檢查 Redis 連線是否正常"""
        try:
            return await self.redis.ping()
        except Exception:
            return False


# --- 全域 MessageBus 存取 ---

_bus: Optional["MessageBus"] = None


def get_bus() -> Optional["MessageBus"]:
    """取得全域 MessageBus（由 main.py lifespan 初始化）"""
    return _bus


def set_bus(bus: "MessageBus"):
    """設定全域 MessageBus"""
    global _bus
    _bus = bus
