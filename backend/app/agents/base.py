"""
Base Agent Class

所有 Agent（Sales, PM, Engineer 等）的基底類別
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from uuid import uuid4
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from app.llm import LLMProvider, LLMProviderFactory, Message
from app.core.execution_mode import (
    ExecutionContext,
    ExecutionController,
    ExecutionMode,
    RunMode,
)
from app.core.action_journal import ActionJournal, ActionType, ActionScope
from app.core.rules_engine import RulesEngine, AgentRules
from app.core.metrics import MetricsCollector

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
class AlternativeAction:
    """考慮過的替代方案"""
    action: str
    params: Dict[str, Any]
    reasoning: str
    excluded_reason: str


@dataclass
class ThinkResult:
    """
    Think 結果

    包含 Agent 的決策過程，讓 CEO 可以理解：
    - 選擇了什麼動作
    - 為什麼選擇這個動作
    - 考慮過哪些其他選項
    - 有多大信心
    - 有哪些不確定因素
    """
    action: str
    params: Dict[str, Any]
    reasoning: str
    requires_approval: bool = False

    # 決策透明度（ADR-005 新增）
    alternatives_considered: List[AlternativeAction] = field(default_factory=list)
    confidence: float = 0.8  # 0.0 - 1.0
    uncertainty_factors: List[str] = field(default_factory=list)
    suggested_review_points: List[str] = field(default_factory=list)

    # 規則檢查結果
    rule_violations: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "action": self.action,
            "params": self.params,
            "reasoning": self.reasoning,
            "requires_approval": self.requires_approval,
            "confidence": self.confidence,
            "alternatives": [
                {
                    "action": alt.action,
                    "excluded_reason": alt.excluded_reason,
                }
                for alt in self.alternatives_considered
            ],
            "uncertainty_factors": self.uncertainty_factors,
            "suggested_review_points": self.suggested_review_points,
            "warnings": self.warnings,
        }


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
        execution_controller: Optional[ExecutionController] = None,
        action_journal: Optional[ActionJournal] = None,
        rules_engine: Optional[RulesEngine] = None,
        metrics_collector: Optional[MetricsCollector] = None,
    ):
        self.config = config
        self.db = db_session
        self.bus = message_bus
        self.llm = llm_provider or LLMProviderFactory.get_current_provider()

        # 可觀測性與可控制性元件（ADR-005）
        self.execution_controller = execution_controller
        self.action_journal = action_journal
        self.rules_engine = rules_engine
        self.metrics = metrics_collector

        # 載入 Agent 規則
        self.rules: Optional[AgentRules] = None
        if self.rules_engine:
            self.rules = self.rules_engine.get_rules(config.id)

        self.status = AgentStatus.IDLE
        self.current_task_id: Optional[str] = None
        self.conversation_history: List[Message] = []

        # 執行上下文（預設自動模式）
        self.execution_context = ExecutionContext.auto()

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

    def set_execution_mode(self, mode: ExecutionMode):
        """設定執行模式"""
        if mode == ExecutionMode.AUTO:
            self.execution_context = ExecutionContext.auto()
        elif mode == ExecutionMode.SUPERVISED:
            self.execution_context = ExecutionContext.supervised()
        elif mode == ExecutionMode.REVIEW:
            self.execution_context = ExecutionContext.review()

    def set_dry_run(self, enabled: bool = True):
        """設定試運行模式"""
        if enabled:
            self.execution_context = ExecutionContext.dry_run()
        else:
            self.execution_context.run_mode = RunMode.LIVE

    async def run_cycle(
        self,
        task_id: Optional[str] = None,
        execution_context: Optional[ExecutionContext] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        執行一次 Sense-Think-Act 迴圈

        支援 Step-by-Step 執行模式（ADR-005）

        Args:
            task_id: 任務 ID
            execution_context: 執行上下文（覆蓋預設）

        Returns:
            執行結果（如果有），否則 None
        """
        ctx = execution_context or self.execution_context
        task_id = task_id or str(uuid4())
        start_time = datetime.now()

        try:
            # 記錄任務接收
            if self.metrics:
                await self.metrics.record_task_received(self.id, task_id)

            # === Checkpoint: Sense ===
            if self.execution_controller:
                await self.execution_controller.create_checkpoint(
                    agent_id=self.id,
                    task_id=task_id,
                    step="sense",
                    context={"status": "starting"},
                    execution_ctx=ctx,
                )

            # 1. Sense: 讀取當前狀態
            context = await self.sense()

            if not context:
                logger.debug(f"[{self.id}] No work to do, staying idle")
                return None

            # === Checkpoint: Think ===
            if self.execution_controller:
                await self.execution_controller.create_checkpoint(
                    agent_id=self.id,
                    task_id=task_id,
                    step="think",
                    context=context,
                    execution_ctx=ctx,
                )

            # 2. Think: 決定下一步
            self.status = AgentStatus.WORKING
            await self._update_db_status()

            result = await self.think(context)

            # 應用規則檢查
            if self.rules:
                rule_check = self.rules_engine.validate_action(
                    agent_id=self.id,
                    action=result.action,
                    params=result.params,
                    context=context,
                )
                if rule_check.get("requires_approval"):
                    result.requires_approval = True
                    result.warnings.append(rule_check.get("approval_reason", ""))

            # === Checkpoint: Pre-Act (審查決策) ===
            if self.execution_controller:
                checkpoint = await self.execution_controller.create_checkpoint(
                    agent_id=self.id,
                    task_id=task_id,
                    step="pre_act",
                    context=context,
                    execution_ctx=ctx,
                )
                checkpoint.proposed_action = result.to_dict()

            # 3. 檢查是否需要審批
            if result.requires_approval:
                approval = await self._request_approval(result)
                if not approval:
                    logger.info(f"[{self.id}] Action rejected by CEO")
                    if self.metrics:
                        await self.metrics.record_ceo_rejection(
                            self.id, task_id, "Action rejected"
                        )
                    return {"status": "rejected", "action": result.action}
                if self.metrics:
                    await self.metrics.record_ceo_approval(self.id, task_id)

            # === Checkpoint: Act ===
            if self.execution_controller:
                await self.execution_controller.create_checkpoint(
                    agent_id=self.id,
                    task_id=task_id,
                    step="act",
                    context={"action": result.action, "params": result.params},
                    execution_ctx=ctx,
                )

            # 4. Act: 執行動作（支援試運行）
            if ctx.run_mode == RunMode.DRY_RUN:
                action_result = {
                    "status": "dry_run",
                    "action": result.action,
                    "would_execute": result.params,
                }
            else:
                # 記錄動作
                if self.action_journal:
                    async with ActionScope(
                        journal=self.action_journal,
                        agent_id=self.id,
                        action_type=ActionType.CUSTOM,
                        action_name=result.action,
                        params=result.params,
                        task_id=task_id,
                    ) as action_record:
                        action_result = await self.act(result)
                        await self.action_journal.complete(
                            action_record.id, action_result, success=True
                        )
                else:
                    action_result = await self.act(result)

            # 5. Log: 記錄
            await self._log_action(result, action_result)

            # 記錄完成
            duration = (datetime.now() - start_time).total_seconds()
            if self.metrics:
                await self.metrics.record_task_completed(self.id, task_id, duration)

            self.status = AgentStatus.IDLE
            await self._update_db_status()

            return action_result

        except Exception as e:
            logger.error(f"[{self.id}] Error in run_cycle: {e}")

            # 記錄失敗
            if self.metrics:
                await self.metrics.record_task_failed(self.id, task_id, str(e))

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
