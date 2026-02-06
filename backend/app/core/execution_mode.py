"""
Execution Mode - Step-by-Step 執行模式

解決問題：Agent 執行過程是黑箱，CEO 無法監督

提供三種執行模式：
- AUTO: 全自動執行
- SUPERVISED: 每步需確認
- REVIEW: Think 後暫停審查
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class ExecutionMode(Enum):
    """執行模式"""
    AUTO = "auto"              # 全自動執行
    SUPERVISED = "supervised"  # 每步需 CEO 確認
    REVIEW = "review"          # Think 後暫停，確認後再 Act


class RunMode(Enum):
    """運行模式（試運行）"""
    LIVE = "live"          # 正式執行
    DRY_RUN = "dry_run"    # 模擬執行，不真正操作
    SHADOW = "shadow"      # 新舊版本同時跑，只採用舊版結果


class CheckpointStatus(Enum):
    """檢查點狀態"""
    PENDING = "pending"        # 等待執行
    EXECUTING = "executing"    # 執行中
    AWAITING_APPROVAL = "awaiting_approval"  # 等待審批
    APPROVED = "approved"      # 已核准
    REJECTED = "rejected"      # 已拒絕
    COMPLETED = "completed"    # 已完成
    SKIPPED = "skipped"        # 已跳過
    FAILED = "failed"          # 失敗


@dataclass
class StepCheckpoint:
    """
    執行檢查點

    記錄 Agent 執行過程中的每個步驟，
    讓 CEO 可以觀察、介入或回滾
    """
    id: str
    agent_id: str
    task_id: str
    step: str  # "sense", "think", "pre_act", "act", "post_act"
    status: CheckpointStatus = CheckpointStatus.PENDING

    # 步驟內容
    context: Dict[str, Any] = field(default_factory=dict)
    proposed_action: Optional[Dict[str, Any]] = None
    result: Optional[Dict[str, Any]] = None

    # 審批資訊
    awaiting_approval: bool = False
    approval_prompt: Optional[str] = None
    approved_by: Optional[str] = None
    approval_feedback: Optional[str] = None

    # 時間戳
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "agent_id": self.agent_id,
            "task_id": self.task_id,
            "step": self.step,
            "status": self.status.value,
            "context": self.context,
            "proposed_action": self.proposed_action,
            "result": self.result,
            "awaiting_approval": self.awaiting_approval,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class ExecutionContext:
    """
    執行上下文

    控制 Agent 的執行行為
    """
    mode: ExecutionMode = ExecutionMode.AUTO
    run_mode: RunMode = RunMode.LIVE

    # 哪些步驟需要暫停
    pause_at_steps: List[str] = field(default_factory=list)

    # 超時設定
    step_timeout_seconds: int = 300
    approval_timeout_seconds: int = 3600  # 1 小時

    # 回調函數
    on_checkpoint: Optional[Callable] = None
    on_approval_needed: Optional[Callable] = None

    @classmethod
    def auto(cls) -> "ExecutionContext":
        """全自動模式"""
        return cls(mode=ExecutionMode.AUTO)

    @classmethod
    def supervised(cls) -> "ExecutionContext":
        """監督模式 - 每步都暫停"""
        return cls(
            mode=ExecutionMode.SUPERVISED,
            pause_at_steps=["sense", "think", "pre_act", "act"],
        )

    @classmethod
    def review(cls) -> "ExecutionContext":
        """審查模式 - Think 後暫停"""
        return cls(
            mode=ExecutionMode.REVIEW,
            pause_at_steps=["pre_act"],
        )

    @classmethod
    def dry_run(cls) -> "ExecutionContext":
        """試運行模式"""
        return cls(
            mode=ExecutionMode.AUTO,
            run_mode=RunMode.DRY_RUN,
        )


class ExecutionController:
    """
    執行控制器

    管理 Agent 執行流程，處理檢查點和審批
    """

    def __init__(self, db_session, websocket_manager=None):
        self.db = db_session
        self.ws = websocket_manager
        self._pending_approvals: Dict[str, asyncio.Future] = {}
        self._checkpoints: Dict[str, StepCheckpoint] = {}

    async def create_checkpoint(
        self,
        agent_id: str,
        task_id: str,
        step: str,
        context: Dict[str, Any],
        execution_ctx: ExecutionContext,
    ) -> StepCheckpoint:
        """建立檢查點"""
        from uuid import uuid4

        checkpoint = StepCheckpoint(
            id=str(uuid4()),
            agent_id=agent_id,
            task_id=task_id,
            step=step,
            context=context,
        )

        self._checkpoints[checkpoint.id] = checkpoint

        # 持久化
        await self._persist_checkpoint(checkpoint)

        # 通知 WebSocket
        if self.ws and execution_ctx.on_checkpoint:
            await execution_ctx.on_checkpoint(checkpoint)

        # 檢查是否需要暫停
        if step in execution_ctx.pause_at_steps:
            checkpoint.status = CheckpointStatus.AWAITING_APPROVAL
            checkpoint.awaiting_approval = True
            await self._persist_checkpoint(checkpoint)

            # 推送審批請求
            await self._push_approval_request(checkpoint)

            # 等待審批
            approved = await self._wait_for_approval(
                checkpoint.id,
                execution_ctx.approval_timeout_seconds,
            )

            if not approved:
                checkpoint.status = CheckpointStatus.REJECTED
                await self._persist_checkpoint(checkpoint)
                raise ExecutionRejectedError(
                    f"Checkpoint {checkpoint.id} rejected by CEO"
                )

            checkpoint.status = CheckpointStatus.APPROVED

        checkpoint.started_at = datetime.utcnow()
        checkpoint.status = CheckpointStatus.EXECUTING
        await self._persist_checkpoint(checkpoint)

        return checkpoint

    async def complete_checkpoint(
        self,
        checkpoint_id: str,
        result: Dict[str, Any],
        success: bool = True,
    ):
        """完成檢查點"""
        checkpoint = self._checkpoints.get(checkpoint_id)
        if not checkpoint:
            return

        checkpoint.result = result
        checkpoint.completed_at = datetime.utcnow()
        checkpoint.status = (
            CheckpointStatus.COMPLETED if success else CheckpointStatus.FAILED
        )

        await self._persist_checkpoint(checkpoint)

    async def approve_checkpoint(
        self,
        checkpoint_id: str,
        approved_by: str,
        feedback: Optional[str] = None,
    ):
        """核准檢查點"""
        checkpoint = self._checkpoints.get(checkpoint_id)
        if not checkpoint:
            raise ValueError(f"Checkpoint {checkpoint_id} not found")

        checkpoint.approved_by = approved_by
        checkpoint.approval_feedback = feedback
        checkpoint.awaiting_approval = False

        # 解除等待
        if checkpoint_id in self._pending_approvals:
            self._pending_approvals[checkpoint_id].set_result(True)

        await self._persist_checkpoint(checkpoint)

    async def reject_checkpoint(
        self,
        checkpoint_id: str,
        rejected_by: str,
        feedback: Optional[str] = None,
    ):
        """拒絕檢查點"""
        checkpoint = self._checkpoints.get(checkpoint_id)
        if not checkpoint:
            raise ValueError(f"Checkpoint {checkpoint_id} not found")

        checkpoint.approved_by = rejected_by
        checkpoint.approval_feedback = feedback
        checkpoint.awaiting_approval = False
        checkpoint.status = CheckpointStatus.REJECTED

        # 解除等待
        if checkpoint_id in self._pending_approvals:
            self._pending_approvals[checkpoint_id].set_result(False)

        await self._persist_checkpoint(checkpoint)

    async def get_pending_approvals(self, agent_id: Optional[str] = None) -> List[StepCheckpoint]:
        """取得待審批的檢查點"""
        pending = [
            cp for cp in self._checkpoints.values()
            if cp.awaiting_approval
        ]

        if agent_id:
            pending = [cp for cp in pending if cp.agent_id == agent_id]

        return pending

    async def _wait_for_approval(
        self,
        checkpoint_id: str,
        timeout_seconds: int,
    ) -> bool:
        """等待審批"""
        future = asyncio.get_event_loop().create_future()
        self._pending_approvals[checkpoint_id] = future

        try:
            result = await asyncio.wait_for(future, timeout=timeout_seconds)
            return result
        except asyncio.TimeoutError:
            logger.warning(f"Approval timeout for checkpoint {checkpoint_id}")
            return False
        finally:
            if checkpoint_id in self._pending_approvals:
                del self._pending_approvals[checkpoint_id]

    async def _push_approval_request(self, checkpoint: StepCheckpoint):
        """推送審批請求到前端"""
        if self.ws:
            await self.ws.broadcast({
                "event": "checkpoint.approval_needed",
                "data": checkpoint.to_dict(),
            })

    async def _persist_checkpoint(self, checkpoint: StepCheckpoint):
        """持久化檢查點到資料庫"""
        # TODO: 實作資料庫寫入
        logger.debug(f"Checkpoint {checkpoint.id}: {checkpoint.status.value}")


class ExecutionRejectedError(Exception):
    """執行被拒絕"""
    pass
