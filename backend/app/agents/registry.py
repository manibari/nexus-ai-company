"""
Agent Registry + Dispatcher

所有 Agent 統一註冊、查詢、派發的中樞。
GATEKEEPER 路由結果透過 dispatch() 實際呼叫目標 Agent。
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable
from uuid import uuid4

logger = logging.getLogger(__name__)


@runtime_checkable
class AgentHandler(Protocol):
    """Agent 必須實作的介面"""

    @property
    def agent_id(self) -> str: ...

    @property
    def agent_name(self) -> str: ...

    async def handle(self, payload: Dict[str, Any]) -> Dict[str, Any]: ...


class AgentRegistry:
    """
    Agent 註冊中心 + 派發器

    職責：
    1. 管理所有已註冊的 Agent
    2. 透過 dispatch() 將任務派發給目標 Agent
    3. 記錄每次 Handoff 到 DB + Activity Log
    """

    def __init__(self, session_factory=None):
        self._agents: Dict[str, AgentHandler] = {}
        self._session_factory = session_factory

    def register(self, handler: AgentHandler):
        """註冊 Agent"""
        agent_id = handler.agent_id
        self._agents[agent_id] = handler
        logger.info(f"Registered agent: {agent_id} ({handler.agent_name})")

    def get(self, agent_id: str) -> Optional[AgentHandler]:
        """取得 Agent"""
        return self._agents.get(agent_id)

    def list_agents(self) -> List[Dict[str, str]]:
        """列出所有已註冊 Agent"""
        return [
            {"id": h.agent_id, "name": h.agent_name}
            for h in self._agents.values()
        ]

    async def dispatch(
        self,
        target_id: str,
        payload: Dict[str, Any],
        from_agent: str = "GATEKEEPER",
    ) -> Dict[str, Any]:
        """
        派發任務給目標 Agent

        流程：
        1. 查找目標 Agent
        2. 記錄 Handoff 到 DB (agent_handoffs table)
        3. 記錄 Activity Log (HANDOFF type)
        4. 呼叫 Agent.handle()
        5. 記錄結果

        Args:
            target_id: 目標 Agent ID (e.g. "PM", "HUNTER")
            payload: 傳遞的資料
            from_agent: 來源 Agent ID

        Returns:
            Agent 處理結果
        """
        handoff_id = f"HO-{uuid4().hex[:8].upper()}"
        handler = self._agents.get(target_id)

        if not handler:
            logger.warning(f"Agent {target_id} not registered, available: {list(self._agents.keys())}")
            return {
                "status": "error",
                "message": f"Agent {target_id} not registered",
                "handoff_id": handoff_id,
            }

        # 1. 記錄 Handoff 開始
        await self._record_handoff(
            handoff_id=handoff_id,
            from_agent=from_agent,
            to_agent=target_id,
            intent=payload.get("intent"),
            payload=payload,
            status="dispatching",
        )

        # 2. 記錄 Activity Log
        from app.agents.activity_log import ActivityType, get_activity_repo
        activity_repo = get_activity_repo()
        await activity_repo.log(
            agent_id=from_agent,
            agent_name=from_agent,
            activity_type=ActivityType.HANDOFF,
            message=f"派發任務給 {target_id}: {payload.get('intent', 'unknown')}",
            metadata={
                "handoff_id": handoff_id,
                "target_agent": target_id,
                "intent": payload.get("intent"),
            },
        )

        # 3. 更新前端狀態為 working
        from app.api.agents import set_agent_idle, set_agent_working
        task_desc = payload.get("title") or payload.get("intent") or "處理中"
        set_agent_working(target_id, task_desc)

        # 4. 呼叫 Agent
        try:
            logger.info(f"[{handoff_id}] Dispatching {from_agent} → {target_id}")
            result = await handler.handle(payload)

            # 5. 記錄成功
            await self._update_handoff(
                handoff_id=handoff_id,
                status="completed",
                result=result,
            )

            await activity_repo.log(
                agent_id=target_id,
                agent_name=handler.agent_name,
                activity_type=ActivityType.TASK_END,
                message=f"完成 {from_agent} 派發的任務",
                metadata={
                    "handoff_id": handoff_id,
                    "result_status": result.get("status"),
                },
            )

            result["handoff_id"] = handoff_id
            return result

        except Exception as e:
            logger.error(f"[{handoff_id}] Dispatch to {target_id} failed: {e}")

            await self._update_handoff(
                handoff_id=handoff_id,
                status="failed",
                result={"error": str(e)},
            )

            await activity_repo.log(
                agent_id=target_id,
                agent_name=handler.agent_name,
                activity_type=ActivityType.ERROR,
                message=f"處理失敗: {e}",
                metadata={"handoff_id": handoff_id, "error": str(e)},
            )

            return {
                "status": "error",
                "message": str(e),
                "handoff_id": handoff_id,
            }
        finally:
            set_agent_idle(target_id)

    async def _record_handoff(
        self,
        handoff_id: str,
        from_agent: str,
        to_agent: str,
        intent: Optional[str],
        payload: Dict,
        status: str,
    ):
        """記錄 Handoff 到 DB"""
        if not self._session_factory:
            return
        try:
            from app.db.models import AgentHandoff
            async with self._session_factory() as session:
                row = AgentHandoff(
                    id=handoff_id,
                    from_agent=from_agent,
                    to_agent=to_agent,
                    intent=intent,
                    payload=payload,
                    status=status,
                    created_at=datetime.utcnow(),
                )
                session.add(row)
                await session.commit()
        except Exception as e:
            logger.error(f"Failed to record handoff: {e}")

    async def _update_handoff(
        self,
        handoff_id: str,
        status: str,
        result: Optional[Dict] = None,
    ):
        """更新 Handoff 結果"""
        if not self._session_factory:
            return
        try:
            from app.db.models import AgentHandoff
            async with self._session_factory() as session:
                row = await session.get(AgentHandoff, handoff_id)
                if row:
                    row.status = status
                    row.result = result
                    row.completed_at = datetime.utcnow()
                    await session.commit()
        except Exception as e:
            logger.error(f"Failed to update handoff: {e}")


# --- 全域 Registry 存取 ---

_registry: Optional[AgentRegistry] = None


def get_registry() -> AgentRegistry:
    """取得全域 AgentRegistry（由 main.py lifespan 初始化）"""
    global _registry
    if _registry is None:
        _registry = AgentRegistry()
    return _registry


def set_registry(registry: AgentRegistry):
    """設定全域 AgentRegistry"""
    global _registry
    _registry = registry
