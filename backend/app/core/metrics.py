"""
Agent Metrics - 績效追蹤

解決問題：無法評估 Agent 表現和成本效益

提供功能：
- 任務完成率
- 響應時間
- CEO 覆寫率
- Token 成本追蹤
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class MetricPeriod(Enum):
    """統計週期"""
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


@dataclass
class AgentMetrics:
    """
    Agent 績效指標
    """
    agent_id: str
    period: MetricPeriod
    period_start: datetime
    period_end: datetime

    # 任務指標
    tasks_received: int = 0
    tasks_completed: int = 0
    tasks_failed: int = 0
    tasks_rejected_by_ceo: int = 0
    tasks_pending: int = 0

    # 時間指標（秒）
    avg_response_time_seconds: float = 0.0
    min_response_time_seconds: float = 0.0
    max_response_time_seconds: float = 0.0
    total_active_time_seconds: float = 0.0
    total_blocked_time_seconds: float = 0.0

    # CEO 介入指標
    ceo_overrides: int = 0
    ceo_approvals: int = 0
    ceo_rejections: int = 0
    actions_marked_mistake: int = 0

    # 成本指標
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_cost_usd: float = 0.0
    avg_cost_per_task_usd: float = 0.0

    # 通訊指標
    messages_sent: int = 0
    messages_received: int = 0
    escalations: int = 0

    # 計算屬性
    @property
    def completion_rate(self) -> float:
        """完成率"""
        if self.tasks_received == 0:
            return 0.0
        return self.tasks_completed / self.tasks_received

    @property
    def failure_rate(self) -> float:
        """失敗率"""
        if self.tasks_received == 0:
            return 0.0
        return self.tasks_failed / self.tasks_received

    @property
    def ceo_override_rate(self) -> float:
        """CEO 覆寫率"""
        total_decisions = self.ceo_approvals + self.ceo_rejections + self.ceo_overrides
        if total_decisions == 0:
            return 0.0
        return (self.ceo_rejections + self.ceo_overrides) / total_decisions

    @property
    def autonomy_rate(self) -> float:
        """自主完成率（無需 CEO 介入）"""
        if self.tasks_completed == 0:
            return 0.0
        autonomous = self.tasks_completed - self.ceo_approvals
        return max(0, autonomous) / self.tasks_completed

    def to_dict(self) -> dict:
        return {
            "agent_id": self.agent_id,
            "period": self.period.value,
            "period_start": self.period_start.isoformat(),
            "period_end": self.period_end.isoformat(),
            "tasks": {
                "received": self.tasks_received,
                "completed": self.tasks_completed,
                "failed": self.tasks_failed,
                "pending": self.tasks_pending,
                "completion_rate": round(self.completion_rate * 100, 2),
            },
            "timing": {
                "avg_response_seconds": round(self.avg_response_time_seconds, 2),
                "total_active_seconds": round(self.total_active_time_seconds, 2),
                "total_blocked_seconds": round(self.total_blocked_time_seconds, 2),
            },
            "ceo_interaction": {
                "overrides": self.ceo_overrides,
                "approvals": self.ceo_approvals,
                "rejections": self.ceo_rejections,
                "override_rate": round(self.ceo_override_rate * 100, 2),
                "autonomy_rate": round(self.autonomy_rate * 100, 2),
            },
            "cost": {
                "total_usd": round(self.total_cost_usd, 4),
                "avg_per_task_usd": round(self.avg_cost_per_task_usd, 4),
                "input_tokens": self.total_input_tokens,
                "output_tokens": self.total_output_tokens,
            },
            "mistakes": self.actions_marked_mistake,
        }


@dataclass
class MetricEvent:
    """指標事件"""
    agent_id: str
    event_type: str
    value: Any
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)


class MetricsCollector:
    """
    指標收集器

    收集和聚合 Agent 績效指標
    """

    def __init__(self, db_session=None):
        self.db = db_session
        self._events: List[MetricEvent] = []
        self._current_metrics: Dict[str, AgentMetrics] = {}

    async def record_task_received(self, agent_id: str, task_id: str):
        """記錄收到任務"""
        await self._record_event(agent_id, "task_received", task_id)
        metrics = self._get_current_metrics(agent_id)
        metrics.tasks_received += 1

    async def record_task_completed(
        self,
        agent_id: str,
        task_id: str,
        duration_seconds: float,
    ):
        """記錄完成任務"""
        await self._record_event(
            agent_id,
            "task_completed",
            task_id,
            {"duration_seconds": duration_seconds},
        )
        metrics = self._get_current_metrics(agent_id)
        metrics.tasks_completed += 1
        self._update_avg_response_time(metrics, duration_seconds)

    async def record_task_failed(
        self,
        agent_id: str,
        task_id: str,
        error: str,
    ):
        """記錄任務失敗"""
        await self._record_event(
            agent_id,
            "task_failed",
            task_id,
            {"error": error},
        )
        metrics = self._get_current_metrics(agent_id)
        metrics.tasks_failed += 1

    async def record_ceo_approval(self, agent_id: str, task_id: str):
        """記錄 CEO 核准"""
        await self._record_event(agent_id, "ceo_approval", task_id)
        metrics = self._get_current_metrics(agent_id)
        metrics.ceo_approvals += 1

    async def record_ceo_rejection(self, agent_id: str, task_id: str, reason: str):
        """記錄 CEO 拒絕"""
        await self._record_event(
            agent_id,
            "ceo_rejection",
            task_id,
            {"reason": reason},
        )
        metrics = self._get_current_metrics(agent_id)
        metrics.ceo_rejections += 1
        metrics.tasks_rejected_by_ceo += 1

    async def record_ceo_override(self, agent_id: str, action: str, reason: str):
        """記錄 CEO 覆寫"""
        await self._record_event(
            agent_id,
            "ceo_override",
            action,
            {"reason": reason},
        )
        metrics = self._get_current_metrics(agent_id)
        metrics.ceo_overrides += 1

    async def record_mistake(self, agent_id: str, action_id: str, feedback: str):
        """記錄標記為錯誤"""
        await self._record_event(
            agent_id,
            "mistake_marked",
            action_id,
            {"feedback": feedback},
        )
        metrics = self._get_current_metrics(agent_id)
        metrics.actions_marked_mistake += 1

    async def record_llm_usage(
        self,
        agent_id: str,
        input_tokens: int,
        output_tokens: int,
        cost_usd: float,
    ):
        """記錄 LLM 使用量"""
        await self._record_event(
            agent_id,
            "llm_usage",
            None,
            {
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "cost_usd": cost_usd,
            },
        )
        metrics = self._get_current_metrics(agent_id)
        metrics.total_input_tokens += input_tokens
        metrics.total_output_tokens += output_tokens
        metrics.total_cost_usd += cost_usd

        # 更新平均成本
        if metrics.tasks_completed > 0:
            metrics.avg_cost_per_task_usd = (
                metrics.total_cost_usd / metrics.tasks_completed
            )

    async def record_blocked_time(self, agent_id: str, duration_seconds: float):
        """記錄阻擋時間"""
        metrics = self._get_current_metrics(agent_id)
        metrics.total_blocked_time_seconds += duration_seconds

    async def record_escalation(self, agent_id: str, target: str, subject: str):
        """記錄升級"""
        await self._record_event(
            agent_id,
            "escalation",
            target,
            {"subject": subject},
        )
        metrics = self._get_current_metrics(agent_id)
        metrics.escalations += 1

    async def get_metrics(
        self,
        agent_id: str,
        period: MetricPeriod = MetricPeriod.DAILY,
    ) -> AgentMetrics:
        """取得 Agent 指標"""
        return self._get_current_metrics(agent_id, period)

    async def get_all_metrics(
        self,
        period: MetricPeriod = MetricPeriod.DAILY,
    ) -> Dict[str, AgentMetrics]:
        """取得所有 Agent 指標"""
        return {
            agent_id: self._get_current_metrics(agent_id, period)
            for agent_id in self._current_metrics
        }

    async def get_summary(self) -> Dict[str, Any]:
        """取得總覽"""
        all_metrics = await self.get_all_metrics()

        total_tasks = sum(m.tasks_completed for m in all_metrics.values())
        total_cost = sum(m.total_cost_usd for m in all_metrics.values())
        total_mistakes = sum(m.actions_marked_mistake for m in all_metrics.values())

        return {
            "agents": len(all_metrics),
            "total_tasks_completed": total_tasks,
            "total_cost_usd": round(total_cost, 4),
            "total_mistakes": total_mistakes,
            "avg_completion_rate": self._avg([m.completion_rate for m in all_metrics.values()]),
            "avg_autonomy_rate": self._avg([m.autonomy_rate for m in all_metrics.values()]),
            "by_agent": {
                agent_id: metrics.to_dict()
                for agent_id, metrics in all_metrics.items()
            },
        }

    async def export_report(
        self,
        period: MetricPeriod,
        format: str = "json",
    ) -> str:
        """匯出報告"""
        import json

        all_metrics = await self.get_all_metrics(period)

        report = {
            "report_type": "agent_performance",
            "period": period.value,
            "generated_at": datetime.utcnow().isoformat(),
            "summary": await self.get_summary(),
            "agents": {
                agent_id: metrics.to_dict()
                for agent_id, metrics in all_metrics.items()
            },
        }

        if format == "json":
            return json.dumps(report, indent=2, ensure_ascii=False)
        else:
            # TODO: 支援其他格式 (csv, html)
            return json.dumps(report, indent=2, ensure_ascii=False)

    def _get_current_metrics(
        self,
        agent_id: str,
        period: MetricPeriod = MetricPeriod.DAILY,
    ) -> AgentMetrics:
        """取得或建立當前週期的指標"""
        key = f"{agent_id}:{period.value}"

        if key not in self._current_metrics:
            now = datetime.utcnow()

            if period == MetricPeriod.HOURLY:
                period_start = now.replace(minute=0, second=0, microsecond=0)
                period_end = period_start + timedelta(hours=1)
            elif period == MetricPeriod.DAILY:
                period_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
                period_end = period_start + timedelta(days=1)
            elif period == MetricPeriod.WEEKLY:
                period_start = now - timedelta(days=now.weekday())
                period_start = period_start.replace(hour=0, minute=0, second=0, microsecond=0)
                period_end = period_start + timedelta(weeks=1)
            else:  # MONTHLY
                period_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                if now.month == 12:
                    period_end = now.replace(year=now.year + 1, month=1, day=1)
                else:
                    period_end = now.replace(month=now.month + 1, day=1)

            self._current_metrics[key] = AgentMetrics(
                agent_id=agent_id,
                period=period,
                period_start=period_start,
                period_end=period_end,
            )

        return self._current_metrics[key]

    def _update_avg_response_time(self, metrics: AgentMetrics, new_duration: float):
        """更新平均響應時間"""
        n = metrics.tasks_completed
        if n == 1:
            metrics.avg_response_time_seconds = new_duration
            metrics.min_response_time_seconds = new_duration
            metrics.max_response_time_seconds = new_duration
        else:
            # 遞增式平均
            metrics.avg_response_time_seconds = (
                (metrics.avg_response_time_seconds * (n - 1) + new_duration) / n
            )
            metrics.min_response_time_seconds = min(
                metrics.min_response_time_seconds, new_duration
            )
            metrics.max_response_time_seconds = max(
                metrics.max_response_time_seconds, new_duration
            )

    async def _record_event(
        self,
        agent_id: str,
        event_type: str,
        value: Any,
        metadata: Dict[str, Any] = None,
    ):
        """記錄事件"""
        event = MetricEvent(
            agent_id=agent_id,
            event_type=event_type,
            value=value,
            metadata=metadata or {},
        )
        self._events.append(event)

        # TODO: 持久化到資料庫

        logger.debug(f"[Metrics] {agent_id}: {event_type} = {value}")

    @staticmethod
    def _avg(values: List[float]) -> float:
        if not values:
            return 0.0
        return round(sum(values) / len(values) * 100, 2)
