"""
Goal Repository

目標儲存與查詢（Tracer Bullet: 使用記憶體儲存）
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional

from app.goals.models import (
    Goal,
    GoalStatus,
    Phase,
    PhaseStatus,
    Checkpoint,
    CheckpointStatus,
    Priority,
    TimeEstimate,
    ChecklistItem,
)

logger = logging.getLogger(__name__)


class GoalRepository:
    """
    目標 Repository

    Tracer Bullet 版本：使用記憶體儲存
    Production 版本：改用 PostgreSQL
    """

    def __init__(self):
        self._goals: Dict[str, Goal] = {}

    async def create(self, goal: Goal) -> Goal:
        """建立目標"""
        self._goals[goal.id] = goal
        logger.info(f"Created goal: {goal.id} - {goal.title}")
        return goal

    async def get(self, goal_id: str) -> Optional[Goal]:
        """取得目標"""
        return self._goals.get(goal_id)

    async def update(self, goal: Goal) -> Goal:
        """更新目標"""
        self._goals[goal.id] = goal
        return goal

    async def delete(self, goal_id: str) -> bool:
        """刪除目標"""
        if goal_id in self._goals:
            del self._goals[goal_id]
            return True
        return False

    async def list(
        self,
        status: Optional[GoalStatus] = None,
        priority: Optional[Priority] = None,
        owner: Optional[str] = None,
        limit: int = 50,
    ) -> List[Goal]:
        """列出目標"""
        goals = list(self._goals.values())

        if status:
            goals = [g for g in goals if g.status == status]
        if priority:
            goals = [g for g in goals if g.priority == priority]
        if owner:
            goals = [g for g in goals if g.owner == owner]

        # 按優先級和建立時間排序
        priority_order = {Priority.CRITICAL: 0, Priority.HIGH: 1, Priority.MEDIUM: 2, Priority.LOW: 3}
        goals.sort(key=lambda g: (priority_order.get(g.priority, 99), g.created_at))

        return goals[:limit]

    async def list_active(self) -> List[Goal]:
        """列出活躍的目標"""
        return await self.list(status=GoalStatus.ACTIVE)

    async def get_overdue(self) -> List[Goal]:
        """取得超時的目標"""
        return [g for g in self._goals.values() if g.is_overdue]

    async def get_at_risk(self) -> List[Goal]:
        """取得有風險的目標"""
        return [g for g in self._goals.values() if g.health == "at_risk"]

    # === Phase Operations ===

    async def get_phase(self, phase_id: str) -> Optional[Phase]:
        """取得階段"""
        for goal in self._goals.values():
            for phase in goal.phases:
                if phase.id == phase_id:
                    return phase
        return None

    async def update_phase(self, phase: Phase) -> Phase:
        """更新階段"""
        goal = await self.get(phase.goal_id)
        if goal:
            for i, p in enumerate(goal.phases):
                if p.id == phase.id:
                    goal.phases[i] = phase
                    break
        return phase

    async def start_phase(self, phase_id: str) -> Optional[Phase]:
        """開始階段"""
        phase = await self.get_phase(phase_id)
        if phase:
            phase.start()
            await self.update_phase(phase)
            logger.info(f"Started phase: {phase_id}")
        return phase

    async def complete_phase(self, phase_id: str) -> Optional[Phase]:
        """完成階段"""
        phase = await self.get_phase(phase_id)
        if phase:
            phase.complete()
            if phase.checkpoint:
                phase.checkpoint.status = CheckpointStatus.AUTO_APPROVED
            await self.update_phase(phase)
            logger.info(f"Completed phase: {phase_id}")
        return phase

    # === Checkpoint Operations ===

    async def approve_checkpoint(
        self,
        phase_id: str,
        approved_by: str,
        comments: Optional[str] = None,
    ) -> Optional[Checkpoint]:
        """核准確認點"""
        phase = await self.get_phase(phase_id)
        if phase and phase.checkpoint:
            phase.checkpoint.status = CheckpointStatus.APPROVED
            phase.checkpoint.reviewed_by = approved_by
            phase.checkpoint.reviewed_at = datetime.utcnow()
            phase.checkpoint.comments = comments
            await self.update_phase(phase)
            logger.info(f"Approved checkpoint for phase: {phase_id}")
            return phase.checkpoint
        return None

    async def reject_checkpoint(
        self,
        phase_id: str,
        rejected_by: str,
        comments: str,
    ) -> Optional[Checkpoint]:
        """退回確認點"""
        phase = await self.get_phase(phase_id)
        if phase and phase.checkpoint:
            phase.checkpoint.status = CheckpointStatus.REJECTED
            phase.checkpoint.reviewed_by = rejected_by
            phase.checkpoint.reviewed_at = datetime.utcnow()
            phase.checkpoint.comments = comments
            phase.status = PhaseStatus.BLOCKED
            await self.update_phase(phase)
            logger.info(f"Rejected checkpoint for phase: {phase_id}")
            return phase.checkpoint
        return None

    async def check_item(
        self,
        phase_id: str,
        item_id: str,
        completed_by: str,
    ) -> bool:
        """勾選檢查項目"""
        phase = await self.get_phase(phase_id)
        if phase and phase.checkpoint:
            for item in phase.checkpoint.checklist:
                if item.id == item_id:
                    item.is_completed = True
                    item.completed_at = datetime.utcnow()
                    item.completed_by = completed_by
                    await self.update_phase(phase)
                    return True
        return False

    # === Statistics ===

    def get_statistics(self) -> Dict:
        """取得統計資訊"""
        goals = list(self._goals.values())

        return {
            "total": len(goals),
            "by_status": {
                status.value: sum(1 for g in goals if g.status == status)
                for status in GoalStatus
            },
            "by_health": {
                health: sum(1 for g in goals if g.health == health)
                for health in ["on_track", "at_risk", "overdue", "completed"]
            },
            "overdue_count": sum(1 for g in goals if g.is_overdue),
            "total_estimated_hours": sum(g.total_estimated_hours for g in goals),
            "total_actual_hours": sum(g.total_actual_hours for g in goals),
        }
