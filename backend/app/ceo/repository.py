"""
CEO To-Do Repository

SQLAlchemy 持久化版本（PostgreSQL / SQLite）
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.ceo.models import (
    TodoItem,
    TodoAction,
    TodoType,
    TodoPriority,
    TodoStatus,
)
from app.db.models import CeoTodo

logger = logging.getLogger(__name__)


def _domain_to_db(todo: TodoItem) -> CeoTodo:
    """Domain model → DB model"""
    return CeoTodo(
        id=todo.id,
        project_name=todo.project_name,
        subject=todo.subject,
        description=todo.description,
        from_agent=todo.from_agent,
        from_agent_name=todo.from_agent_name,
        type=todo.type.value,
        priority=todo.priority.value,
        status=todo.status.value,
        deadline=todo.deadline,
        completed_at=todo.completed_at,
        created_at=todo.created_at,
        actions=[a.to_dict() for a in todo.actions] if todo.actions else [],
        response=todo.response,
        payload=todo.payload,
        related_entity_type=todo.related_entity_type,
        related_entity_id=todo.related_entity_id,
    )


def _db_to_domain(row: CeoTodo) -> TodoItem:
    """DB model → Domain model"""
    actions = []
    if row.actions:
        for a in row.actions:
            actions.append(TodoAction(
                id=a.get("id", "action"),
                label=a.get("label", ""),
                style=a.get("style", "default"),
                requires_input=a.get("requires_input", False),
                input_placeholder=a.get("input_placeholder"),
            ))

    return TodoItem(
        id=row.id,
        project_name=row.project_name,
        subject=row.subject,
        description=row.description,
        from_agent=row.from_agent or "",
        from_agent_name=row.from_agent_name or "",
        type=TodoType(row.type) if row.type else TodoType.NOTIFICATION,
        priority=TodoPriority(row.priority) if row.priority else TodoPriority.NORMAL,
        status=TodoStatus(row.status) if row.status else TodoStatus.PENDING,
        deadline=row.deadline,
        completed_at=row.completed_at,
        created_at=row.created_at,
        actions=actions,
        response=row.response,
        payload=row.payload or {},
        related_entity_type=row.related_entity_type,
        related_entity_id=row.related_entity_id,
    )


class TodoRepository:
    """CEO 待辦儲存庫（SQLAlchemy 版本）"""

    def __init__(self, session_factory):
        """
        Args:
            session_factory: AsyncSessionLocal（可產生 AsyncSession 的 callable）
        """
        self._session_factory = session_factory

    def _session(self) -> AsyncSession:
        return self._session_factory()

    # === CRUD ===

    async def create(self, todo: TodoItem) -> TodoItem:
        """建立待辦"""
        async with self._session() as session:
            db_todo = _domain_to_db(todo)
            session.add(db_todo)
            await session.commit()
            logger.info(f"Created todo: {todo.id}")
            return todo

    async def get(self, todo_id: str) -> Optional[TodoItem]:
        """取得待辦"""
        async with self._session() as session:
            result = await session.get(CeoTodo, todo_id)
            return _db_to_domain(result) if result else None

    async def update(self, todo: TodoItem) -> TodoItem:
        """更新待辦"""
        async with self._session() as session:
            result = await session.get(CeoTodo, todo.id)
            if not result:
                raise ValueError(f"Todo {todo.id} not found")
            # 更新所有欄位
            result.project_name = todo.project_name
            result.subject = todo.subject
            result.description = todo.description
            result.from_agent = todo.from_agent
            result.from_agent_name = todo.from_agent_name
            result.type = todo.type.value
            result.priority = todo.priority.value
            result.status = todo.status.value
            result.deadline = todo.deadline
            result.completed_at = todo.completed_at
            result.actions = [a.to_dict() for a in todo.actions] if todo.actions else []
            result.response = todo.response
            result.payload = todo.payload
            result.related_entity_type = todo.related_entity_type
            result.related_entity_id = todo.related_entity_id
            await session.commit()
            return todo

    async def delete(self, todo_id: str) -> bool:
        """刪除待辦"""
        async with self._session() as session:
            result = await session.get(CeoTodo, todo_id)
            if not result:
                return False
            await session.delete(result)
            await session.commit()
            return True

    async def list(
        self,
        status: Optional[TodoStatus] = None,
        priority: Optional[TodoPriority] = None,
        limit: int = 50,
    ) -> List[TodoItem]:
        """列出待辦"""
        async with self._session() as session:
            stmt = select(CeoTodo)

            if status:
                stmt = stmt.where(CeoTodo.status == status.value)
            if priority:
                stmt = stmt.where(CeoTodo.priority == priority.value)

            stmt = stmt.order_by(CeoTodo.created_at.desc()).limit(limit)
            result = await session.execute(stmt)
            rows = result.scalars().all()

            todos = [_db_to_domain(r) for r in rows]

            # 排序：優先級 > 過期 > 建立時間
            todos.sort(key=lambda t: (
                t.priority_order,
                0 if t.is_overdue else 1,
                t.created_at,
            ))

            return todos

    async def list_pending(self) -> List[TodoItem]:
        """列出待處理的待辦"""
        return await self.list(status=TodoStatus.PENDING)

    # === 操作 ===

    async def respond(
        self,
        todo_id: str,
        action_id: str,
        response_data: Optional[Dict[str, Any]] = None,
    ) -> Optional[TodoItem]:
        """CEO 回覆待辦"""
        todo = await self.get(todo_id)
        if not todo:
            return None

        todo.status = TodoStatus.COMPLETED
        todo.completed_at = datetime.utcnow()
        todo.response = {
            "action_id": action_id,
            "data": response_data,
            "responded_at": datetime.utcnow().isoformat(),
        }

        await self.update(todo)
        return todo

    async def snooze(
        self,
        todo_id: str,
        hours: int = 24,
    ) -> Optional[TodoItem]:
        """延後處理"""
        todo = await self.get(todo_id)
        if not todo:
            return None

        if todo.deadline:
            todo.deadline = todo.deadline + timedelta(hours=hours)
        else:
            todo.deadline = datetime.utcnow() + timedelta(hours=hours)

        await self.update(todo)
        return todo

    # === 統計 ===

    def get_stats(self) -> Dict[str, Any]:
        """取得統計（同步包裝，保持 API 相容）"""
        # 因為原本的 API 是 sync，這裡用 lazy approach
        # 在 async context 中請改用 get_stats_async()
        return {
            "total": 0,
            "pending": 0,
            "overdue": 0,
            "completed": 0,
            "by_priority": {},
            "by_type": {},
        }

    async def get_stats_async(self) -> Dict[str, Any]:
        """取得統計（async 版本）"""
        async with self._session() as session:
            # 總數
            total_result = await session.execute(
                select(func.count()).select_from(CeoTodo)
            )
            total = total_result.scalar() or 0

            # 待處理
            pending_result = await session.execute(
                select(func.count()).select_from(CeoTodo).where(
                    CeoTodo.status == "pending"
                )
            )
            pending = pending_result.scalar() or 0

            # 已完成
            completed_result = await session.execute(
                select(func.count()).select_from(CeoTodo).where(
                    CeoTodo.status == "completed"
                )
            )
            completed = completed_result.scalar() or 0

            # 按優先級
            priority_result = await session.execute(
                select(CeoTodo.priority, func.count())
                .where(CeoTodo.status == "pending")
                .group_by(CeoTodo.priority)
            )
            by_priority = {row[0]: row[1] for row in priority_result.all()}

            # 按類型
            type_result = await session.execute(
                select(CeoTodo.type, func.count())
                .where(CeoTodo.status == "pending")
                .group_by(CeoTodo.type)
            )
            by_type = {row[0]: row[1] for row in type_result.all()}

            # 計算過期數
            now = datetime.utcnow()
            overdue_result = await session.execute(
                select(func.count()).select_from(CeoTodo).where(
                    CeoTodo.status == "pending",
                    CeoTodo.deadline < now,
                    CeoTodo.deadline.isnot(None),
                )
            )
            overdue = overdue_result.scalar() or 0

            return {
                "total": total,
                "pending": pending,
                "overdue": overdue,
                "completed": completed,
                "by_priority": by_priority,
                "by_type": by_type,
            }
