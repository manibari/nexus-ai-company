"""
Task Lifecycle Repository

Session-per-operation pattern（同 ProductRepository）。

Issue #14
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import select

from app.task.models import (
    generate_task_id,
    generate_event_id,
    generate_plan_id,
    generate_trace_id,
)

logger = logging.getLogger(__name__)


# === Global accessor ===

_task_repo: Optional["TaskLifecycleRepository"] = None


def get_task_repo() -> "TaskLifecycleRepository":
    """取得共享的 TaskLifecycleRepository 實例"""
    global _task_repo
    if _task_repo is None:
        from app.db.database import AsyncSessionLocal
        _task_repo = TaskLifecycleRepository(session_factory=AsyncSessionLocal)
    return _task_repo


def set_task_repo(repo: "TaskLifecycleRepository") -> None:
    """設定共享實例（用於測試注入）"""
    global _task_repo
    _task_repo = repo


# === Repository ===

class TaskLifecycleRepository:
    """SQLAlchemy-backed repository for task lifecycle"""

    def __init__(self, session_factory=None):
        self._session_factory = session_factory

    def _session(self):
        return self._session_factory()

    async def create_task(
        self,
        intent: str,
        priority: int = 2,
        source: str = "intake",
        trace_id: Optional[str] = None,
        title: Optional[str] = None,
        description: Optional[str] = None,
    ) -> Dict[str, Any]:
        """建立 lifecycle task（status=submitted）"""
        from app.db.models import Task

        task_id = generate_task_id()
        if trace_id is None:
            trace_id = generate_trace_id()

        now = datetime.utcnow()

        async with self._session() as session:
            task = Task(
                id=task_id,
                title=title or f"Task: {intent}",
                description=description,
                pipeline="lifecycle",
                stage="submitted",
                priority=priority,
                lifecycle_status="submitted",
                retry_count=0,
                trace_id=trace_id,
                source=source,
                created_at=now,
                updated_at=now,
            )
            session.add(task)
            await session.commit()

        logger.info(f"Created lifecycle task: {task_id} (intent={intent})")
        return {
            "id": task_id,
            "title": task.title,
            "lifecycle_status": "submitted",
            "trace_id": trace_id,
            "source": source,
            "priority": priority,
            "created_at": now.isoformat(),
        }

    async def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """取得 task 詳情"""
        from app.db.models import Task

        async with self._session() as session:
            row = await session.get(Task, task_id)
            if not row:
                return None
            return self._task_to_dict(row)

    async def list_tasks(
        self,
        status: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """列出 lifecycle tasks"""
        from app.db.models import Task

        async with self._session() as session:
            stmt = select(Task).where(Task.pipeline == "lifecycle")

            if status:
                stmt = stmt.where(Task.lifecycle_status == status)

            stmt = stmt.order_by(Task.created_at.desc()).limit(limit)
            result = await session.execute(stmt)
            rows = result.scalars().all()

        return [self._task_to_dict(r) for r in rows]

    async def update_lifecycle_status(
        self,
        task_id: str,
        new_status: str,
        retry_count: Optional[int] = None,
    ) -> Optional[Dict[str, Any]]:
        """更新 lifecycle_status"""
        from app.db.models import Task

        async with self._session() as session:
            row = await session.get(Task, task_id)
            if not row:
                return None

            row.lifecycle_status = new_status
            row.stage = new_status
            row.updated_at = datetime.utcnow()
            if retry_count is not None:
                row.retry_count = retry_count
            if new_status == "completed":
                row.completed_at = datetime.utcnow()
            await session.commit()

        return await self.get_task(task_id)

    async def record_event(
        self,
        task_id: str,
        event_type: str,
        actor: str,
        from_status: Optional[str] = None,
        to_status: Optional[str] = None,
        payload: Optional[Dict[str, Any]] = None,
        trace_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """記錄不可變事件"""
        from app.db.models import TaskEvent

        event_id = generate_event_id()
        now = datetime.utcnow()

        async with self._session() as session:
            event = TaskEvent(
                id=event_id,
                task_id=task_id,
                event_type=event_type,
                actor=actor,
                from_status=from_status,
                to_status=to_status,
                payload=payload or {},
                trace_id=trace_id,
                created_at=now,
            )
            session.add(event)
            await session.commit()

        return {
            "id": event_id,
            "task_id": task_id,
            "event_type": event_type,
            "actor": actor,
            "from_status": from_status,
            "to_status": to_status,
            "payload": payload or {},
            "trace_id": trace_id,
            "created_at": now.isoformat(),
        }

    async def get_task_events(self, task_id: str) -> List[Dict[str, Any]]:
        """取得 task 的事件歷史"""
        from app.db.models import TaskEvent

        async with self._session() as session:
            stmt = (
                select(TaskEvent)
                .where(TaskEvent.task_id == task_id)
                .order_by(TaskEvent.created_at.asc())
            )
            result = await session.execute(stmt)
            rows = result.scalars().all()

        return [
            {
                "id": r.id,
                "task_id": r.task_id,
                "event_type": r.event_type,
                "actor": r.actor,
                "from_status": r.from_status,
                "to_status": r.to_status,
                "payload": r.payload,
                "trace_id": r.trace_id,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ]

    async def save_execution_plan(
        self,
        task_id: str,
        plan_json: Dict[str, Any],
        routing_risk: float = 0.0,
        risk_factors: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """儲存執行計畫"""
        from app.db.models import ExecutionPlan

        plan_id = generate_plan_id()
        now = datetime.utcnow()

        # 計算版本號
        existing = await self.get_execution_plan(task_id)
        version = (existing["version"] + 1) if existing else 1

        async with self._session() as session:
            plan = ExecutionPlan(
                id=plan_id,
                task_id=task_id,
                version=version,
                plan_json=plan_json,
                routing_risk=routing_risk,
                risk_factors=risk_factors or [],
                status="draft",
                created_at=now,
            )
            session.add(plan)
            await session.commit()

        return {
            "id": plan_id,
            "task_id": task_id,
            "version": version,
            "plan_json": plan_json,
            "routing_risk": routing_risk,
            "risk_factors": risk_factors or [],
            "status": "draft",
            "created_at": now.isoformat(),
        }

    async def get_execution_plan(self, task_id: str) -> Optional[Dict[str, Any]]:
        """取得最新的執行計畫"""
        from app.db.models import ExecutionPlan

        async with self._session() as session:
            stmt = (
                select(ExecutionPlan)
                .where(ExecutionPlan.task_id == task_id)
                .order_by(ExecutionPlan.version.desc())
                .limit(1)
            )
            result = await session.execute(stmt)
            row = result.scalars().first()

            if not row:
                return None

            return {
                "id": row.id,
                "task_id": row.task_id,
                "version": row.version,
                "plan_json": row.plan_json,
                "routing_risk": row.routing_risk,
                "risk_factors": row.risk_factors,
                "status": row.status,
                "created_at": row.created_at.isoformat() if row.created_at else None,
                "approved_at": row.approved_at.isoformat() if row.approved_at else None,
            }

    async def approve_plan(self, task_id: str) -> Optional[Dict[str, Any]]:
        """核准最新的執行計畫"""
        from app.db.models import ExecutionPlan

        async with self._session() as session:
            stmt = (
                select(ExecutionPlan)
                .where(ExecutionPlan.task_id == task_id)
                .order_by(ExecutionPlan.version.desc())
                .limit(1)
            )
            result = await session.execute(stmt)
            row = result.scalars().first()

            if not row:
                return None

            row.status = "approved"
            row.approved_at = datetime.utcnow()
            await session.commit()

            return {
                "id": row.id,
                "task_id": row.task_id,
                "version": row.version,
                "status": "approved",
                "approved_at": row.approved_at.isoformat(),
            }

    @staticmethod
    def _task_to_dict(row) -> Dict[str, Any]:
        """Task ORM → dict"""
        return {
            "id": row.id,
            "title": row.title,
            "description": row.description,
            "pipeline": row.pipeline,
            "stage": row.stage,
            "lifecycle_status": row.lifecycle_status,
            "retry_count": row.retry_count,
            "trace_id": row.trace_id,
            "source": row.source,
            "assigned_to": row.assigned_to,
            "priority": row.priority,
            "created_at": row.created_at.isoformat() if row.created_at else None,
            "updated_at": row.updated_at.isoformat() if row.updated_at else None,
            "completed_at": row.completed_at.isoformat() if row.completed_at else None,
        }
