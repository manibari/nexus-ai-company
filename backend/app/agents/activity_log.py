"""
Agent Activity Log

記錄 Agent 的工作活動日誌
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any
from enum import Enum


class ActivityType(Enum):
    """活動類型"""
    TASK_START = "task_start"      # 開始任務
    TASK_END = "task_end"          # 結束任務
    STATUS_CHANGE = "status_change" # 狀態變更
    BLOCKED = "blocked"            # 遭遇阻塞
    UNBLOCKED = "unblocked"        # 解除阻塞
    MESSAGE = "message"            # 一般訊息
    ERROR = "error"                # 錯誤
    MILESTONE = "milestone"        # 里程碑


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


class ActivityLogRepository:
    """活動日誌儲存庫"""

    def __init__(self):
        self._logs: List[ActivityEntry] = []
        self._counter = 0
        self._task_starts: Dict[str, datetime] = {}  # agent_id -> start_time

    def _generate_id(self) -> str:
        self._counter += 1
        return f"ACT-{datetime.now().strftime('%Y%m%d%H%M%S')}-{self._counter:04d}"

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
        duration = None

        # 計算任務耗時
        if activity_type == ActivityType.TASK_START:
            self._task_starts[agent_id] = datetime.utcnow()
        elif activity_type == ActivityType.TASK_END:
            start_time = self._task_starts.pop(agent_id, None)
            if start_time:
                duration = int((datetime.utcnow() - start_time).total_seconds())

        entry = ActivityEntry(
            id=self._generate_id(),
            agent_id=agent_id,
            agent_name=agent_name,
            activity_type=activity_type,
            message=message,
            project_id=project_id,
            project_name=project_name,
            duration_seconds=duration,
            metadata=metadata or {},
        )

        self._logs.append(entry)

        # 保留最近 500 條記錄
        if len(self._logs) > 500:
            self._logs = self._logs[-500:]

        return entry

    async def get_recent(
        self,
        limit: int = 50,
        agent_id: Optional[str] = None,
        project_id: Optional[str] = None,
    ) -> List[ActivityEntry]:
        """取得最近的活動日誌"""
        logs = self._logs

        if agent_id:
            logs = [l for l in logs if l.agent_id == agent_id]

        if project_id:
            logs = [l for l in logs if l.project_id == project_id]

        # 按時間倒序
        logs = sorted(logs, key=lambda x: x.timestamp, reverse=True)

        return logs[:limit]

    async def get_agent_timeline(self, agent_id: str, limit: int = 20) -> List[ActivityEntry]:
        """取得特定 Agent 的時間線"""
        logs = [l for l in self._logs if l.agent_id == agent_id]
        logs = sorted(logs, key=lambda x: x.timestamp, reverse=True)
        return logs[:limit]

    def get_stats(self) -> Dict[str, Any]:
        """取得統計資料"""
        from collections import Counter

        type_counts = Counter(l.activity_type.value for l in self._logs)
        agent_counts = Counter(l.agent_id for l in self._logs)

        return {
            "total_entries": len(self._logs),
            "by_type": dict(type_counts),
            "by_agent": dict(agent_counts),
            "active_tasks": len(self._task_starts),
        }

    async def get_agent_daily_summary(self, agent_id: str, date: Optional[datetime] = None) -> Dict[str, Any]:
        """取得特定 Agent 的每日摘要"""
        if date is None:
            date = datetime.utcnow()

        # 篩選當日的日誌
        start_of_day = date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = date.replace(hour=23, minute=59, second=59, microsecond=999999)

        daily_logs = [
            l for l in self._logs
            if l.agent_id == agent_id and start_of_day <= l.timestamp <= end_of_day
        ]

        # 計算總工時
        total_seconds = 0
        tasks = []
        task_pairs = {}  # 用於配對 start/end

        for log in sorted(daily_logs, key=lambda x: x.timestamp):
            if log.activity_type == ActivityType.TASK_START:
                task_pairs[log.message] = {
                    "start_time": log.timestamp.strftime("%H:%M:%S"),
                    "end_time": None,
                    "message": log.message.replace("開始任務: ", ""),
                    "status": "in_progress",
                    "duration_seconds": 0,
                }
            elif log.activity_type == ActivityType.TASK_END:
                task_msg = log.message.replace("完成任務: ", "")
                # 找到對應的開始記錄
                for key, task in task_pairs.items():
                    if task_msg in key or key.replace("開始任務: ", "") == task_msg:
                        task["end_time"] = log.timestamp.strftime("%H:%M:%S")
                        task["status"] = "completed"
                        if log.duration_seconds:
                            task["duration_seconds"] = log.duration_seconds
                            total_seconds += log.duration_seconds
                        break
                else:
                    # 沒找到配對，直接加入
                    if log.duration_seconds:
                        total_seconds += log.duration_seconds
                        tasks.append({
                            "start_time": None,
                            "end_time": log.timestamp.strftime("%H:%M:%S"),
                            "message": task_msg,
                            "status": "completed",
                            "duration_seconds": log.duration_seconds,
                            "duration_formatted": self._format_duration(log.duration_seconds),
                        })

        # 處理進行中的任務
        for key, task in task_pairs.items():
            if task["status"] == "in_progress":
                # 計算進行中的時間
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

        # 按開始時間排序
        tasks = sorted(tasks, key=lambda x: x.get("start_time") or "00:00:00", reverse=True)

        # 取得 agent 名稱
        agent_name = agent_id
        for log in daily_logs:
            if log.agent_name:
                agent_name = log.agent_name
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
        if date is None:
            date = datetime.utcnow()

        # 找出當日有活動的所有 agent
        start_of_day = date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = date.replace(hour=23, minute=59, second=59, microsecond=999999)

        agent_ids = set(
            l.agent_id for l in self._logs
            if start_of_day <= l.timestamp <= end_of_day
        )

        summaries = []
        for agent_id in agent_ids:
            summary = await self.get_agent_daily_summary(agent_id, date)
            summaries.append(summary)

        # 按工時排序
        summaries = sorted(summaries, key=lambda x: x["total_work_seconds"], reverse=True)
        return summaries

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
_activity_repo = ActivityLogRepository()


def get_activity_repo() -> ActivityLogRepository:
    return _activity_repo
