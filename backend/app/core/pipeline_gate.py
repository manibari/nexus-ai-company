"""
Pipeline Gate - 關卡機制與人工覆寫

解決問題：Pipeline 狀態轉換無法暫停或人工介入

提供功能：
- 階段關卡（Approval Gate, Condition Gate, Time Gate）
- 人工覆寫（暫停、恢復、強制跳轉、跳過）
- 可配置的關卡規則
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class GateType(Enum):
    """關卡類型"""
    APPROVAL = "approval"      # 需要審批
    CONDITION = "condition"    # 滿足條件
    TIME = "time"              # 時間等待
    NOTIFICATION = "notification"  # 通知（不阻擋）


class GateStatus(Enum):
    """關卡狀態"""
    OPEN = "open"              # 開放通過
    CLOSED = "closed"          # 關閉
    AWAITING = "awaiting"      # 等待中
    PASSED = "passed"          # 已通過
    REJECTED = "rejected"      # 已拒絕
    BYPASSED = "bypassed"      # 被覆寫繞過


class OverrideAction(Enum):
    """覆寫動作"""
    PAUSE = "pause"            # 暫停處理
    RESUME = "resume"          # 恢復處理
    FORCE_STAGE = "force_stage"  # 強制跳轉階段
    SKIP = "skip"              # 跳過當前階段
    RETRY = "retry"            # 重試
    ABORT = "abort"            # 中止


@dataclass
class GateCondition:
    """關卡條件"""
    field: str                 # 檢查的欄位
    operator: str              # 運算符: >, <, ==, !=, in, contains
    value: Any                 # 比較值
    description: str = ""      # 條件說明


@dataclass
class PipelineGate:
    """
    Pipeline 關卡

    定義進入某個階段前需要通過的關卡
    """
    id: str
    pipeline: str              # "sales" or "product"
    stage: str                 # 目標階段
    gate_type: GateType

    # 關卡設定
    requires_approval: bool = False
    approval_roles: List[str] = field(default_factory=lambda: ["CEO"])
    conditions: List[GateCondition] = field(default_factory=list)
    wait_seconds: int = 0      # Time Gate 的等待時間
    auto_approve_after_seconds: int = 0  # 自動放行時間，0=永不自動

    # 通知設定
    notify_on_enter: bool = False
    notify_roles: List[str] = field(default_factory=list)

    # 狀態
    status: GateStatus = GateStatus.OPEN
    enabled: bool = True

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "pipeline": self.pipeline,
            "stage": self.stage,
            "gate_type": self.gate_type.value,
            "requires_approval": self.requires_approval,
            "enabled": self.enabled,
        }


@dataclass
class PipelineOverride:
    """
    人工覆寫記錄
    """
    id: str
    entity_type: str           # "lead", "task"
    entity_id: str
    action: OverrideAction
    target_stage: Optional[str] = None  # 用於 FORCE_STAGE
    reason: str = ""
    override_by: str = "CEO"
    created_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "entity_id": self.entity_id,
            "action": self.action.value,
            "target_stage": self.target_stage,
            "reason": self.reason,
            "override_by": self.override_by,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class EntityState:
    """實體狀態（用於追蹤暫停等狀態）"""
    entity_type: str
    entity_id: str
    current_stage: str
    paused: bool = False
    paused_at: Optional[datetime] = None
    paused_reason: Optional[str] = None
    awaiting_gate: Optional[str] = None  # 等待的關卡 ID


class PipelineGateManager:
    """
    Pipeline 關卡管理器

    管理所有關卡規則和人工覆寫
    """

    def __init__(self, db_session, websocket_manager=None):
        self.db = db_session
        self.ws = websocket_manager
        self._gates: Dict[str, PipelineGate] = {}
        self._entity_states: Dict[str, EntityState] = {}
        self._pending_approvals: Dict[str, asyncio.Future] = {}
        self._overrides: List[PipelineOverride] = []

    def register_gate(self, gate: PipelineGate):
        """註冊關卡"""
        gate_key = f"{gate.pipeline}:{gate.stage}"
        self._gates[gate_key] = gate
        logger.info(f"Registered gate: {gate_key} ({gate.gate_type.value})")

    def load_gates_from_config(self, config: Dict[str, Any]):
        """從配置載入關卡"""
        for pipeline_name, pipeline_config in config.items():
            gates = pipeline_config.get("gates", [])
            for gate_config in gates:
                gate = PipelineGate(
                    id=f"{pipeline_name}_{gate_config['stage']}",
                    pipeline=pipeline_name,
                    stage=gate_config["stage"],
                    gate_type=GateType(gate_config.get("type", "approval")),
                    requires_approval=gate_config.get("requires_approval", False),
                    conditions=[
                        GateCondition(**c) for c in gate_config.get("conditions", [])
                    ],
                    auto_approve_after_seconds=gate_config.get(
                        "auto_approve_after_seconds", 0
                    ),
                    notify_on_enter=gate_config.get("notify_on_enter", False),
                )
                self.register_gate(gate)

    async def check_gate(
        self,
        pipeline: str,
        target_stage: str,
        entity_id: str,
        entity_data: Dict[str, Any],
    ) -> tuple[bool, Optional[str]]:
        """
        檢查是否可以進入目標階段

        Returns:
            (can_proceed, reason)
        """
        gate_key = f"{pipeline}:{target_stage}"
        gate = self._gates.get(gate_key)

        # 沒有關卡，直接通過
        if not gate or not gate.enabled:
            return True, None

        # 檢查實體是否被暫停
        entity_state = self._get_entity_state(entity_id)
        if entity_state and entity_state.paused:
            return False, f"Entity is paused: {entity_state.paused_reason}"

        # 檢查條件關卡
        if gate.conditions:
            for condition in gate.conditions:
                if not self._evaluate_condition(condition, entity_data):
                    return False, f"Condition not met: {condition.description}"

        # 檢查審批關卡
        if gate.requires_approval:
            approved = await self._request_gate_approval(gate, entity_id, entity_data)
            if not approved:
                return False, "Approval rejected"

        # 通知
        if gate.notify_on_enter:
            await self._send_notification(gate, entity_id, entity_data)

        return True, None

    async def override(
        self,
        entity_type: str,
        entity_id: str,
        action: OverrideAction,
        target_stage: Optional[str] = None,
        reason: str = "",
        override_by: str = "CEO",
    ) -> PipelineOverride:
        """
        執行人工覆寫
        """
        from uuid import uuid4

        override = PipelineOverride(
            id=str(uuid4()),
            entity_type=entity_type,
            entity_id=entity_id,
            action=action,
            target_stage=target_stage,
            reason=reason,
            override_by=override_by,
        )

        self._overrides.append(override)

        # 執行覆寫動作
        if action == OverrideAction.PAUSE:
            await self._pause_entity(entity_id, reason)
        elif action == OverrideAction.RESUME:
            await self._resume_entity(entity_id)
        elif action == OverrideAction.FORCE_STAGE:
            if target_stage:
                await self._force_stage(entity_type, entity_id, target_stage)
        elif action == OverrideAction.SKIP:
            await self._skip_current(entity_type, entity_id)
        elif action == OverrideAction.ABORT:
            await self._abort_entity(entity_type, entity_id)

        # 記錄
        await self._persist_override(override)

        logger.info(
            f"[Override] {action.value} on {entity_type}:{entity_id} "
            f"by {override_by}: {reason}"
        )

        return override

    async def pause(
        self,
        entity_id: str,
        reason: str = "",
        paused_by: str = "CEO",
    ):
        """暫停實體處理"""
        return await self.override(
            entity_type="unknown",  # 會在內部識別
            entity_id=entity_id,
            action=OverrideAction.PAUSE,
            reason=reason,
            override_by=paused_by,
        )

    async def resume(
        self,
        entity_id: str,
        resumed_by: str = "CEO",
    ):
        """恢復實體處理"""
        return await self.override(
            entity_type="unknown",
            entity_id=entity_id,
            action=OverrideAction.RESUME,
            override_by=resumed_by,
        )

    async def force_stage(
        self,
        entity_type: str,
        entity_id: str,
        target_stage: str,
        reason: str = "",
        forced_by: str = "CEO",
    ):
        """強制跳轉階段"""
        return await self.override(
            entity_type=entity_type,
            entity_id=entity_id,
            action=OverrideAction.FORCE_STAGE,
            target_stage=target_stage,
            reason=reason,
            override_by=forced_by,
        )

    async def get_entity_state(self, entity_id: str) -> Optional[EntityState]:
        """取得實體狀態"""
        return self._entity_states.get(entity_id)

    async def get_pending_gates(self) -> List[Dict[str, Any]]:
        """取得等待審批的關卡"""
        pending = []
        for entity_id, state in self._entity_states.items():
            if state.awaiting_gate:
                pending.append({
                    "entity_id": entity_id,
                    "gate_id": state.awaiting_gate,
                    "current_stage": state.current_stage,
                })
        return pending

    def _get_entity_state(self, entity_id: str) -> Optional[EntityState]:
        return self._entity_states.get(entity_id)

    def _evaluate_condition(
        self,
        condition: GateCondition,
        entity_data: Dict[str, Any],
    ) -> bool:
        """評估條件"""
        value = entity_data.get(condition.field)
        target = condition.value

        if condition.operator == ">":
            return value > target
        elif condition.operator == "<":
            return value < target
        elif condition.operator == ">=":
            return value >= target
        elif condition.operator == "<=":
            return value <= target
        elif condition.operator == "==":
            return value == target
        elif condition.operator == "!=":
            return value != target
        elif condition.operator == "in":
            return value in target
        elif condition.operator == "contains":
            return target in value
        else:
            return False

    async def _request_gate_approval(
        self,
        gate: PipelineGate,
        entity_id: str,
        entity_data: Dict[str, Any],
    ) -> bool:
        """請求關卡審批"""
        # 推送到前端
        if self.ws:
            await self.ws.broadcast({
                "event": "gate.approval_needed",
                "data": {
                    "gate_id": gate.id,
                    "entity_id": entity_id,
                    "stage": gate.stage,
                    "entity_data": entity_data,
                },
            })

        # 建立等待
        future = asyncio.get_event_loop().create_future()
        self._pending_approvals[f"{gate.id}:{entity_id}"] = future

        try:
            if gate.auto_approve_after_seconds > 0:
                result = await asyncio.wait_for(
                    future,
                    timeout=gate.auto_approve_after_seconds,
                )
                return result
            else:
                # 無限等待
                return await future
        except asyncio.TimeoutError:
            # 自動放行
            logger.info(f"Gate {gate.id} auto-approved after timeout")
            return True

    async def approve_gate(self, gate_id: str, entity_id: str, approved_by: str):
        """核准關卡"""
        key = f"{gate_id}:{entity_id}"
        if key in self._pending_approvals:
            self._pending_approvals[key].set_result(True)
            logger.info(f"Gate {gate_id} approved for {entity_id} by {approved_by}")

    async def reject_gate(self, gate_id: str, entity_id: str, rejected_by: str):
        """拒絕關卡"""
        key = f"{gate_id}:{entity_id}"
        if key in self._pending_approvals:
            self._pending_approvals[key].set_result(False)
            logger.info(f"Gate {gate_id} rejected for {entity_id} by {rejected_by}")

    async def _pause_entity(self, entity_id: str, reason: str):
        state = self._entity_states.get(entity_id)
        if state:
            state.paused = True
            state.paused_at = datetime.utcnow()
            state.paused_reason = reason

    async def _resume_entity(self, entity_id: str):
        state = self._entity_states.get(entity_id)
        if state:
            state.paused = False
            state.paused_at = None
            state.paused_reason = None

    async def _force_stage(self, entity_type: str, entity_id: str, target_stage: str):
        # TODO: 實作強制跳轉
        pass

    async def _skip_current(self, entity_type: str, entity_id: str):
        # TODO: 實作跳過當前
        pass

    async def _abort_entity(self, entity_type: str, entity_id: str):
        # TODO: 實作中止
        pass

    async def _send_notification(
        self,
        gate: PipelineGate,
        entity_id: str,
        entity_data: Dict[str, Any],
    ):
        if self.ws:
            await self.ws.broadcast({
                "event": "gate.notification",
                "data": {
                    "gate_id": gate.id,
                    "entity_id": entity_id,
                    "stage": gate.stage,
                },
            })

    async def _persist_override(self, override: PipelineOverride):
        # TODO: 持久化
        pass
