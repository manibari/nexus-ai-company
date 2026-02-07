"""
Agent Activity Log

記錄 Agent 的工作活動日誌（SQLAlchemy 持久化版本 — PostgreSQL / SQLite）
"""

import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from enum import Enum

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class ActivityType(Enum):
    """活動類型"""
    TASK_START = "task_start"       # 開始任務
    TASK_END = "task_end"           # 結束任務
    STATUS_CHANGE = "status_change" # 狀態變更
    BLOCKED = "blocked"             # 遭遇阻塞
    UNBLOCKED = "unblocked"         # 解除阻塞
    MESSAGE = "message"             # 一般訊息
    ERROR = "error"                 # 錯誤
    MILESTONE = "milestone"         # 里程碑
    HANDOFF = "handoff"             # Agent 互轉


@dataclass
class ActivityEntry:
    """活動日誌條目"""
    id: str
    agent_id: str
    agent_name: str
    activity_type: ActivityType
    message: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    project_id: Optional[str] = None
    project_name: Optional[str] = None
    duration_seconds: Optional[int] = None  # 任務耗時
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "agent_id": self.agent_id,
            "agent_name": self.agent_name,
            "activity_type": self.activity_type.value,
            "message": self.message,
            "timestamp": self.timestamp.isoformat(),
            "project_id": self.project_id,
            "project_name": self.project_name,
            "duration_seconds": self.duration_seconds,
            "metadata": self.metadata,
        }


def _db_to_entry(row) -> ActivityEntry:
    """DB model → ActivityEntry"""
    metadata = {}
    if row.metadata_json:
        if isinstance(row.metadata_json, dict):
            metadata = row.metadata_json
        elif isinstance(row.metadata_json, str):
            try:
                metadata = json.loads(row.metadata_json)
            except json.JSONDecodeError:
                pass

    return ActivityEntry(
        id=row.id,
        agent_id=row.agent_id,
        agent_name=row.agent_name,
        activity_type=ActivityType(row.activity_type),
        message=row.message,
        timestamp=row.timestamp,
        project_id=row.project_id,
        project_name=row.project_name,
        duration_seconds=row.duration_seconds,
        metadata=metadata,
    )


class ActivityLogRepository:
    """活動日誌儲存庫（SQLAlchemy 版本）"""

    def __init__(self, session_factory=None):
        self._session_factory = session_factory
        self._task_starts: Dict[str, datetime] = {}  # agent_id -> start_time（記憶體快取）

    def _session(self) -> AsyncSession:
        return self._session_factory()

    @staticmethod
    def _generate_id() -> str:
        """生成唯一 ID"""
        return f"ACT-{datetime.now().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:4].upper()}"

    async def log(
        self,
        agent_id: str,
        agent_name: str,
        activity_type: ActivityType,
        message: str,
        project_id: Optional[str] = None,
        project_name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ActivityEntry:
        """記錄活動"""
        from app.db.models import ActivityLog

        duration = None

        # 計算任務耗時
        if activity_type == ActivityType.TASK_START:
            self._task_starts[agent_id] = datetime.utcnow()
        elif activity_type == ActivityType.TASK_END:
            start_time = self._task_starts.pop(agent_id, None)
            if start_time:
                duration = int((datetime.utcnow() - start_time).total_seconds())

        entry_id = self._generate_id()
        now = datetime.utcnow()

        entry = ActivityEntry(
            id=entry_id,
            agent_id=agent_id,
            agent_name=agent_name,
            activity_type=activity_type,
            message=message,
            timestamp=now,
            project_id=project_id,
            project_name=project_name,
            duration_seconds=duration,
            metadata=metadata or {},
        )

        # 寫入資料庫
        async with self._session() as session:
            db_row = ActivityLog(
                id=entry_id,
                agent_id=agent_id,
                agent_name=agent_name,
                activity_type=activity_type.value,
                message=message,
                timestamp=now,
                project_id=project_id,
                project_name=project_name,
                duration_seconds=duration,
                metadata_json=metadata if metadata else None,
            )
            session.add(db_row)
            await session.commit()

        return entry

    async def get_recent(
        self,
        limit: int = 50,
        agent_id: Optional[str] = None,
        project_id: Optional[str] = None,
    ) -> List[ActivityEntry]:
        """取得最近的活動日誌"""
        from app.db.models import ActivityLog

        async with self._session() as session:
            stmt = select(ActivityLog)

            conditions = []
            if agent_id:
                conditions.append(ActivityLog.agent_id == agent_id)
            if project_id:
                conditions.append(ActivityLog.project_id == project_id)
            if conditions:
                stmt = stmt.where(and_(*conditions))

            stmt = stmt.order_by(ActivityLog.timestamp.desc()).limit(limit)
            result = await session.execute(stmt)
            rows = result.scalars().all()

            return [_db_to_entry(row) for row in rows]

    async def get_agent_timeline(self, agent_id: str, limit: int = 20) -> List[ActivityEntry]:
        """取得特定 Agent 的時間線"""
        return await self.get_recent(limit=limit, agent_id=agent_id)

    async def get_stats(self) -> Dict[str, Any]:
        """取得統計資料"""
        from app.db.models import ActivityLog

        async with self._session() as session:
            # 總數
            total_result = await session.execute(
                select(func.count()).select_from(ActivityLog)
            )
            total = total_result.scalar() or 0

            # 按類型統計
            type_result = await session.execute(
                select(ActivityLog.activity_type, func.count())
                .group_by(ActivityLog.activity_type)
            )
            by_type = {row[0]: row[1] for row in type_result.all()}

            # 按 Agent 統計
            agent_result = await session.execute(
                select(ActivityLog.agent_id, func.count())
                .group_by(ActivityLog.agent_id)
            )
            by_agent = {row[0]: row[1] for row in agent_result.all()}

            return {
                "total_entries": total,
                "by_type": by_type,
                "by_agent": by_agent,
                "active_tasks": len(self._task_starts),
            }

    async def get_agent_daily_summary(self, agent_id: str, date: Optional[datetime] = None) -> Dict[str, Any]:
        """取得特定 Agent 的每日摘要"""
        from app.db.models import ActivityLog

        if date is None:
            date = datetime.utcnow()

        start_of_day = date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = date.replace(hour=23, minute=59, second=59, microsecond=999999)

        async with self._session() as session:
            stmt = (
                select(ActivityLog)
                .where(
                    ActivityLog.agent_id == agent_id,
                    ActivityLog.timestamp >= start_of_day,
                    ActivityLog.timestamp <= end_of_day,
                )
                .order_by(ActivityLog.timestamp.asc())
            )
            result = await session.execute(stmt)
            daily_logs = [_db_to_entry(row) for row in result.scalars().all()]

        # 計算總工時
        total_seconds = 0
        tasks = []
        task_pairs = {}

        for log_entry in daily_logs:
            if log_entry.activity_type == ActivityType.TASK_START:
                task_pairs[log_entry.message] = {
                    "start_time": log_entry.timestamp.strftime("%H:%M:%S"),
                    "end_time": None,
                    "message": log_entry.message.replace("開始任務: ", "").replace("處理功能需求: ", "").replace("分析 CEO 指令: ", ""),
                    "status": "in_progress",
                    "duration_seconds": 0,
                }
            elif log_entry.activity_type == ActivityType.TASK_END:
                task_msg = log_entry.message.replace("完成任務: ", "").replace("已建立 PRD: ", "").replace("分析完成: ", "")
                for key, task in task_pairs.items():
                    if task_msg in key or any(part in task_msg for part in key.split()):
                        task["end_time"] = log_entry.timestamp.strftime("%H:%M:%S")
                        task["status"] = "completed"
                        if log_entry.duration_seconds:
                            task["duration_seconds"] = log_entry.duration_seconds
                            total_seconds += log_entry.duration_seconds
                        break
                else:
                    if log_entry.duration_seconds:
                        total_seconds += log_entry.duration_seconds
                        tasks.append({
                            "start_time": None,
                            "end_time": log_entry.timestamp.strftime("%H:%M:%S"),
                            "message": task_msg,
                            "status": "completed",
                            "duration_seconds": log_entry.duration_seconds,
                            "duration_formatted": self._format_duration(log_entry.duration_seconds),
                        })

        # 處理進行中的任務
        for key, task in task_pairs.items():
            if task["status"] == "in_progress":
                start_time = datetime.strptime(task["start_time"], "%H:%M:%S").replace(
                    year=date.year, month=date.month, day=date.day
                )
                elapsed = int((datetime.utcnow() - start_time).total_seconds())
                task["duration_seconds"] = elapsed
                task["duration_formatted"] = self._format_duration(elapsed) + "+"
                total_seconds += elapsed
            else:
                task["duration_formatted"] = self._format_duration(task["duration_seconds"])
            tasks.append(task)

        tasks = sorted(tasks, key=lambda x: x.get("start_time") or "00:00:00", reverse=True)

        agent_name = agent_id
        for log_entry in daily_logs:
            if log_entry.agent_name:
                agent_name = log_entry.agent_name
                break

        return {
            "agent_id": agent_id,
            "agent_name": agent_name,
            "date": date.strftime("%Y-%m-%d"),
            "total_work_seconds": total_seconds,
            "total_work_formatted": self._format_duration(total_seconds),
            "task_count": len(tasks),
            "tasks": tasks,
        }

    async def get_all_agents_daily_summary(self, date: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """取得所有 Agent 的每日摘要"""
        from app.db.models import ActivityLog

        if date is None:
            date = datetime.utcnow()

        start_of_day = date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = date.replace(hour=23, minute=59, second=59, microsecond=999999)

        async with self._session() as session:
            stmt = (
                select(ActivityLog.agent_id)
                .where(
                    ActivityLog.timestamp >= start_of_day,
                    ActivityLog.timestamp <= end_of_day,
                )
                .distinct()
            )
            result = await session.execute(stmt)
            agent_ids = [row[0] for row in result.all()]

        summaries = []
        for aid in agent_ids:
            summary = await self.get_agent_daily_summary(aid, date)
            summaries.append(summary)

        summaries = sorted(summaries, key=lambda x: x["total_work_seconds"], reverse=True)
        return summaries

    async def cleanup_old_logs(self, days: int = 30):
        """清理舊日誌"""
        from app.db.models import ActivityLog

        cutoff = datetime.utcnow() - timedelta(days=days)

        async with self._session() as session:
            stmt = select(ActivityLog).where(ActivityLog.timestamp < cutoff)
            result = await session.execute(stmt)
            rows = result.scalars().all()
            deleted = len(rows)
            for row in rows:
                await session.delete(row)
            await session.commit()

        logger.info(f"Cleaned up {deleted} old activity logs (older than {days} days)")
        return deleted

    @staticmethod
    def _format_duration(seconds: int) -> str:
        """格式化時間長度"""
        if seconds < 60:
            return f"{seconds}s"
        elif seconds < 3600:
            minutes = seconds // 60
            secs = seconds % 60
            return f"{minutes}m {secs}s" if secs else f"{minutes}m"
        else:
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            return f"{hours}h {minutes}m" if minutes else f"{hours}h"


# 全域實例
_activity_repo: Optional[ActivityLogRepository] = None


def get_activity_repo() -> ActivityLogRepository:
    global _activity_repo
    if _activity_repo is None:
        from app.db.database import AsyncSessionLocal
        _activity_repo = ActivityLogRepository(session_factory=AsyncSessionLocal)
    return _activity_repo
