"""
Base Agent Class

所有 Agent（Sales, PM, Engineer 等）的基底類別
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from app.llm import LLMProvider, LLMProviderFactory, Message

logger = logging.getLogger(__name__)


class AgentStatus(Enum):
    """Agent 狀態"""
    IDLE = "idle"
    WORKING = "working"
    BLOCKED_INTERNAL = "blocked_internal"
    BLOCKED_USER = "blocked_user"


@dataclass
class AgentConfig:
    """Agent 配置"""
    id: str
    name: str
    role: str
    system_prompt: str
    tools: List[str] = field(default_factory=list)
    temperature: float = 0.7
    max_tokens: int = 4096


@dataclass
class ThinkResult:
    """Think 結果"""
    action: str
    params: Dict[str, Any]
    reasoning: str
    requires_approval: bool = False


class Agent(ABC):
    """
    Agent 基底類別

    實作 Sense-Think-Act 迴圈：
    1. Sense: 從資料庫讀取當前狀態
    2. Think: 使用 LLM 決定下一步行動
    3. Act: 執行工具或更新狀態
    4. Log: 記錄所有操作
    """

    def __init__(
        self,
        config: AgentConfig,
        db_session,
        message_bus,
        llm_provider: Optional[LLMProvider] = None,
    ):
        self.config = config
        self.db = db_session
        self.bus = message_bus
        self.llm = llm_provider or LLMProviderFactory.get_current_provider()

        self.status = AgentStatus.IDLE
        self.current_task_id: Optional[str] = None
        self.conversation_history: List[Message] = []

        # 初始化 system prompt
        self._init_system_prompt()

    def _init_system_prompt(self):
        """初始化 system prompt"""
        self.conversation_history = [
            Message(role="system", content=self.config.system_prompt)
        ]

    @property
    def id(self) -> str:
        return self.config.id

    @property
    def name(self) -> str:
        return self.config.name

    # === Sense-Think-Act 迴圈 ===

    async def run_cycle(self) -> Optional[Dict[str, Any]]:
        """
        執行一次 Sense-Think-Act 迴圈

        Returns:
            執行結果（如果有），否則 None
        """
        try:
            # 1. Sense: 讀取當前狀態
            context = await self.sense()

            if not context:
                logger.debug(f"[{self.id}] No work to do, staying idle")
                return None

            # 2. Think: 決定下一步
            self.status = AgentStatus.WORKING
            await self._update_db_status()

            result = await self.think(context)

            # 3. 檢查是否需要審批
            if result.requires_approval:
                approval = await self._request_approval(result)
                if not approval:
                    logger.info(f"[{self.id}] Action rejected by CEO")
                    return {"status": "rejected", "action": result.action}

            # 4. Act: 執行動作
            action_result = await self.act(result)

            # 5. Log: 記錄
            await self._log_action(result, action_result)

            self.status = AgentStatus.IDLE
            await self._update_db_status()

            return action_result

        except Exception as e:
            logger.error(f"[{self.id}] Error in run_cycle: {e}")
            self.status = AgentStatus.IDLE
            await self._update_db_status()
            raise

    @abstractmethod
    async def sense(self) -> Optional[Dict[str, Any]]:
        """
        感知環境：讀取當前任務、訊息、狀態

        Returns:
            當前上下文，如果沒有工作則返回 None
        """
        pass

    async def think(self, context: Dict[str, Any]) -> ThinkResult:
        """
        思考：使用 LLM 分析上下文並決定行動

        Args:
            context: 當前上下文

        Returns:
            ThinkResult: 決定的行動
        """
        # 構建 prompt
        user_message = self._build_think_prompt(context)
        self.conversation_history.append(Message(role="user", content=user_message))

        # 呼叫 LLM
        response = await self.llm.chat(
            messages=self.conversation_history,
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens,
        )

        # 記錄 LLM 呼叫成本
        await self._record_llm_cost(response)

        # 加入對話歷史
        self.conversation_history.append(
            Message(role="assistant", content=response.content)
        )

        # 解析回應
        return self._parse_think_response(response.content)

    @abstractmethod
    async def act(self, result: ThinkResult) -> Dict[str, Any]:
        """
        執行行動

        Args:
            result: Think 階段的結果

        Returns:
            執行結果
        """
        pass

    # === 輔助方法 ===

    def _build_think_prompt(self, context: Dict[str, Any]) -> str:
        """構建 Think 階段的 prompt"""
        return f"""
Current Context:
{self._format_context(context)}

Based on the above context, decide what action to take next.
Respond in the following JSON format:
{{
    "action": "action_name",
    "params": {{}},
    "reasoning": "why you chose this action",
    "requires_approval": false
}}

Available actions for your role:
{self._get_available_actions()}
"""

    def _format_context(self, context: Dict[str, Any]) -> str:
        """格式化上下文"""
        lines = []
        for key, value in context.items():
            lines.append(f"- {key}: {value}")
        return "\n".join(lines)

    @abstractmethod
    def _get_available_actions(self) -> str:
        """取得可用的行動列表（由子類實作）"""
        pass

    def _parse_think_response(self, response: str) -> ThinkResult:
        """解析 LLM 回應"""
        import json

        try:
            # 嘗試解析 JSON
            # 處理可能包含 markdown code block 的情況
            if "```json" in response:
                response = response.split("```json")[1].split("```")[0]
            elif "```" in response:
                response = response.split("```")[1].split("```")[0]

            data = json.loads(response.strip())

            return ThinkResult(
                action=data.get("action", "wait"),
                params=data.get("params", {}),
                reasoning=data.get("reasoning", ""),
                requires_approval=data.get("requires_approval", False),
            )
        except json.JSONDecodeError:
            logger.warning(f"[{self.id}] Failed to parse LLM response as JSON")
            return ThinkResult(
                action="wait",
                params={},
                reasoning="Failed to parse response",
                requires_approval=False,
            )

    async def _request_approval(self, result: ThinkResult) -> bool:
        """請求 CEO 審批"""
        self.status = AgentStatus.BLOCKED_USER
        await self._update_db_status()

        response = await self.bus.escalate_to_ceo(
            from_agent=self.id,
            subject=f"Approval needed: {result.action}",
            payload={
                "action": result.action,
                "params": result.params,
                "reasoning": result.reasoning,
            },
            blocking=True,
        )

        self.status = AgentStatus.WORKING
        await self._update_db_status()

        return response.payload.get("approved", False)

    async def _update_db_status(self):
        """更新資料庫中的狀態"""
        # TODO: Implement database update
        pass

    async def _log_action(self, result: ThinkResult, action_result: Dict[str, Any]):
        """記錄行動"""
        # TODO: Implement logging
        logger.info(
            f"[{self.id}] Action: {result.action}, "
            f"Result: {action_result.get('status', 'unknown')}"
        )

    async def _record_llm_cost(self, response):
        """記錄 LLM 呼叫成本"""
        # TODO: Implement cost recording to ledger
        logger.debug(
            f"[{self.id}] LLM call: {response.input_tokens} in, "
            f"{response.output_tokens} out, ${response.cost_usd}"
        )

    # === Message Bus 互動 ===

    async def query_agent(
        self, target: str, subject: str, payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """查詢其他 Agent"""
        self.status = AgentStatus.BLOCKED_INTERNAL
        await self._update_db_status()

        try:
            response = await self.bus.query(target, subject, payload)
            return response.payload
        finally:
            self.status = AgentStatus.WORKING
            await self._update_db_status()

    async def notify_agent(
        self, target: str, subject: str, payload: Dict[str, Any]
    ):
        """通知其他 Agent（不等待回應）"""
        await self.bus.send(target, subject, payload)
