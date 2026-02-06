"""
Goal-Driven Execution Models

目標導向執行的資料模型
時間單位：分鐘（AI Agent 以分鐘計算）
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4


class GoalStatus(Enum):
    """目標狀態"""
    DRAFT = "draft"           # 草稿
    PENDING = "pending"       # 待確認
    ACTIVE = "active"         # 執行中
    COMPLETED = "completed"   # 已完成
    CANCELLED = "cancelled"   # 已取消
    ON_HOLD = "on_hold"       # 暫停


class PhaseStatus(Enum):
    """階段狀態"""
    PENDING = "pending"       # 待開始
    IN_PROGRESS = "in_progress"  # 執行中
    REVIEW = "review"         # 待審查
    COMPLETED = "completed"   # 已完成
    BLOCKED = "blocked"       # 被阻塞
    SKIPPED = "skipped"       # 跳過


class CheckpointStatus(Enum):
    """確認點狀態"""
    PENDING = "pending"       # 待確認
    APPROVED = "approved"     # 已核准
    REJECTED = "rejected"     # 已退回
    AUTO_APPROVED = "auto_approved"  # 自動核准


class Priority(Enum):
    """優先級"""
    CRITICAL = "critical"     # 緊急
    HIGH = "high"             # 高
    MEDIUM = "medium"         # 中
    LOW = "low"               # 低


@dataclass
class TimeEstimate:
    """時間估算（以分鐘為單位）"""
    estimated_minutes: int        # 預估分鐘數
    actual_minutes: int = 0       # 實際分鐘數
    buffer_minutes: int = 0       # 緩衝分鐘數

    @property
    def remaining_minutes(self) -> int:
        return max(0, self.estimated_minutes - self.actual_minutes)

    @property
    def is_over_estimate(self) -> bool:
        return self.actual_minutes > self.estimated_minutes

    @property
    def completion_percentage(self) -> float:
        if self.estimated_minutes == 0:
            return 100.0
        return min(100.0, (self.actual_minutes / self.estimated_minutes) * 100)

    @property
    def estimated_hours(self) -> float:
        """轉換為小時（顯示用）"""
        return self.estimated_minutes / 60

    @property
    def actual_hours(self) -> float:
        """轉換為小時（顯示用）"""
        return self.actual_minutes / 60

    def to_dict(self) -> Dict[str, Any]:
        return {
            "estimated_minutes": self.estimated_minutes,
            "actual_minutes": self.actual_minutes,
            "buffer_minutes": self.buffer_minutes,
            "remaining_minutes": self.remaining_minutes,
            "estimated_hours": round(self.estimated_hours, 2),
            "actual_hours": round(self.actual_hours, 2),
            "is_over_estimate": self.is_over_estimate,
            "completion_percentage": round(self.completion_percentage, 1),
        }


@dataclass
class ChecklistItem:
    """檢查項目"""
    id: str
    description: str
    is_completed: bool = False
    completed_at: Optional[datetime] = None
    completed_by: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "description": self.description,
            "is_completed": self.is_completed,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "completed_by": self.completed_by,
        }


@dataclass
class Checkpoint:
    """確認點"""
    id: str
    phase_id: str

    # 檢查項目
    checklist: List[ChecklistItem] = field(default_factory=list)

    # 審查者
    auto_check: bool = True           # 是否自動檢查
    requires_ceo_approval: bool = False  # 是否需要 CEO 核准

    # 狀態
    status: CheckpointStatus = CheckpointStatus.PENDING

    # 結果
    comments: Optional[str] = None
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[datetime] = None

    def __post_init__(self):
        if not self.id:
            self.id = f"CP-{uuid4().hex[:8].upper()}"

    @property
    def all_checked(self) -> bool:
        return all(item.is_completed for item in self.checklist)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "phase_id": self.phase_id,
            "checklist": [item.to_dict() for item in self.checklist],
            "auto_check": self.auto_check,
            "requires_ceo_approval": self.requires_ceo_approval,
            "status": self.status.value,
            "all_checked": self.all_checked,
            "comments": self.comments,
            "reviewed_by": self.reviewed_by,
            "reviewed_at": self.reviewed_at.isoformat() if self.reviewed_at else None,
        }


@dataclass
class Phase:
    """執行階段"""
    id: str
    goal_id: str
    name: str
    objective: str

    # 順序
    sequence: int = 0

    # 交付物與驗收標準
    deliverables: List[str] = field(default_factory=list)
    acceptance_criteria: List[str] = field(default_factory=list)

    # 時間（以分鐘計算）
    time_estimate: TimeEstimate = field(default_factory=lambda: TimeEstimate(estimated_minutes=30))
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    deadline: Optional[datetime] = None  # 絕對截止時間

    # 狀態
    status: PhaseStatus = PhaseStatus.PENDING

    # 依賴
    depends_on: List[str] = field(default_factory=list)  # phase IDs

    # 指派
    assignee: Optional[str] = None  # Agent ID

    # 確認點
    checkpoint: Optional[Checkpoint] = None

    # 備註
    notes: Optional[str] = None
    blockers: List[str] = field(default_factory=list)

    def __post_init__(self):
        if not self.id:
            self.id = f"PH-{uuid4().hex[:8].upper()}"
        # 自動建立 checkpoint
        if self.checkpoint is None:
            self.checkpoint = Checkpoint(
                id=f"CP-{self.id[3:]}",
                phase_id=self.id,
                checklist=[
                    ChecklistItem(id=f"CK-{i}", description=criteria)
                    for i, criteria in enumerate(self.acceptance_criteria)
                ]
            )

    @property
    def is_overdue(self) -> bool:
        if self.deadline and self.status not in [PhaseStatus.COMPLETED, PhaseStatus.SKIPPED]:
            return datetime.utcnow() > self.deadline
        return False

    @property
    def progress(self) -> float:
        """計算階段進度"""
        if self.status == PhaseStatus.COMPLETED:
            return 100.0
        if self.status == PhaseStatus.PENDING:
            return 0.0
        if self.checkpoint and self.checkpoint.checklist:
            completed = sum(1 for item in self.checkpoint.checklist if item.is_completed)
            return (completed / len(self.checkpoint.checklist)) * 100
        return 50.0  # IN_PROGRESS 預設 50%

    @property
    def elapsed_minutes(self) -> int:
        """已經過的分鐘數"""
        if self.started_at:
            if self.completed_at:
                return int((self.completed_at - self.started_at).total_seconds() / 60)
            return int((datetime.utcnow() - self.started_at).total_seconds() / 60)
        return 0

    def start(self):
        """開始階段"""
        self.status = PhaseStatus.IN_PROGRESS
        self.started_at = datetime.utcnow()
        # 設定截止時間
        if not self.deadline:
            total_minutes = self.time_estimate.estimated_minutes + self.time_estimate.buffer_minutes
            self.deadline = self.started_at + timedelta(minutes=total_minutes)

    def complete(self):
        """完成階段"""
        self.status = PhaseStatus.COMPLETED
        self.completed_at = datetime.utcnow()
        if self.started_at:
            self.time_estimate.actual_minutes = int((self.completed_at - self.started_at).total_seconds() / 60)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "goal_id": self.goal_id,
            "name": self.name,
            "objective": self.objective,
            "sequence": self.sequence,
            "deliverables": self.deliverables,
            "acceptance_criteria": self.acceptance_criteria,
            "time_estimate": self.time_estimate.to_dict(),
            "elapsed_minutes": self.elapsed_minutes,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "deadline": self.deadline.isoformat() if self.deadline else None,
            "status": self.status.value,
            "progress": round(self.progress, 1),
            "is_overdue": self.is_overdue,
            "depends_on": self.depends_on,
            "assignee": self.assignee,
            "checkpoint": self.checkpoint.to_dict() if self.checkpoint else None,
            "notes": self.notes,
            "blockers": self.blockers,
        }


@dataclass
class Goal:
    """目標"""
    id: str
    title: str
    objective: str

    # 成功標準
    success_criteria: List[str] = field(default_factory=list)

    # 邊界
    in_scope: List[str] = field(default_factory=list)
    out_of_scope: List[str] = field(default_factory=list)

    # 時間（以分鐘計算）
    time_estimate: TimeEstimate = field(default_factory=lambda: TimeEstimate(estimated_minutes=120))
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    deadline: Optional[datetime] = None

    # 狀態
    status: GoalStatus = GoalStatus.DRAFT
    priority: Priority = Priority.MEDIUM

    # 階段
    phases: List[Phase] = field(default_factory=list)

    # 人員
    owner: str = "ORCHESTRATOR"
    assignees: List[str] = field(default_factory=list)
    created_by: Optional[str] = None

    # 來源
    source_input_id: Optional[str] = None  # 來自 CEO Intake 的 ID

    # 備註
    notes: Optional[str] = None

    def __post_init__(self):
        if not self.id:
            self.id = f"GOAL-{datetime.now().strftime('%Y%m%d')}-{uuid4().hex[:4].upper()}"

    @property
    def progress(self) -> float:
        """計算目標進度"""
        if not self.phases:
            return 0.0
        total_weight = sum(p.time_estimate.estimated_minutes for p in self.phases)
        if total_weight == 0:
            return 0.0
        weighted_progress = sum(
            (p.progress / 100) * p.time_estimate.estimated_minutes
            for p in self.phases
        )
        return (weighted_progress / total_weight) * 100

    @property
    def current_phase(self) -> Optional[Phase]:
        """取得目前執行中的階段"""
        for phase in self.phases:
            if phase.status == PhaseStatus.IN_PROGRESS:
                return phase
        return None

    @property
    def next_phase(self) -> Optional[Phase]:
        """取得下一個待執行的階段"""
        for phase in sorted(self.phases, key=lambda p: p.sequence):
            if phase.status == PhaseStatus.PENDING:
                # 檢查依賴
                deps_completed = all(
                    any(p.id == dep_id and p.status == PhaseStatus.COMPLETED for p in self.phases)
                    for dep_id in phase.depends_on
                )
                if deps_completed:
                    return phase
        return None

    @property
    def is_overdue(self) -> bool:
        if self.deadline and self.status not in [GoalStatus.COMPLETED, GoalStatus.CANCELLED]:
            return datetime.utcnow() > self.deadline
        return False

    @property
    def health(self) -> str:
        """計算目標健康度"""
        if self.status == GoalStatus.COMPLETED:
            return "completed"
        if self.is_overdue:
            return "overdue"
        # 檢查是否有 phase 超時
        if any(p.is_overdue for p in self.phases):
            return "at_risk"
        # 檢查進度是否落後
        if self.deadline and self.started_at:
            time_elapsed = (datetime.utcnow() - self.started_at).total_seconds() / 60
            total_time = (self.deadline - self.started_at).total_seconds() / 60
            expected_progress = (time_elapsed / total_time) * 100 if total_time > 0 else 0
            if self.progress < expected_progress - 20:  # 落後 20% 以上
                return "at_risk"
        return "on_track"

    @property
    def total_estimated_minutes(self) -> int:
        """總預估分鐘數"""
        return sum(p.time_estimate.estimated_minutes for p in self.phases)

    @property
    def total_actual_minutes(self) -> int:
        """總實際分鐘數"""
        return sum(p.time_estimate.actual_minutes for p in self.phases)

    @property
    def elapsed_minutes(self) -> int:
        """已經過的分鐘數"""
        if self.started_at:
            if self.completed_at:
                return int((self.completed_at - self.started_at).total_seconds() / 60)
            return int((datetime.utcnow() - self.started_at).total_seconds() / 60)
        return 0

    def start(self):
        """開始目標"""
        self.status = GoalStatus.ACTIVE
        self.started_at = datetime.utcnow()
        # 設定截止時間（如果沒有）
        if not self.deadline:
            total_minutes = self.time_estimate.estimated_minutes + self.time_estimate.buffer_minutes
            self.deadline = self.started_at + timedelta(minutes=total_minutes)

    def complete(self):
        """完成目標"""
        self.status = GoalStatus.COMPLETED
        self.completed_at = datetime.utcnow()
        if self.started_at:
            self.time_estimate.actual_minutes = int((self.completed_at - self.started_at).total_seconds() / 60)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "objective": self.objective,
            "success_criteria": self.success_criteria,
            "in_scope": self.in_scope,
            "out_of_scope": self.out_of_scope,
            "time_estimate": self.time_estimate.to_dict(),
            "elapsed_minutes": self.elapsed_minutes,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "deadline": self.deadline.isoformat() if self.deadline else None,
            "status": self.status.value,
            "priority": self.priority.value,
            "progress": round(self.progress, 1),
            "health": self.health,
            "phases": [p.to_dict() for p in self.phases],
            "current_phase": self.current_phase.to_dict() if self.current_phase else None,
            "owner": self.owner,
            "assignees": self.assignees,
            "total_estimated_minutes": self.total_estimated_minutes,
            "total_actual_minutes": self.total_actual_minutes,
            "notes": self.notes,
        }

    def to_summary(self) -> Dict[str, Any]:
        """簡化的摘要格式"""
        return {
            "id": self.id,
            "title": self.title,
            "status": self.status.value,
            "priority": self.priority.value,
            "progress": round(self.progress, 1),
            "health": self.health,
            "deadline": self.deadline.isoformat() if self.deadline else None,
            "is_overdue": self.is_overdue,
            "elapsed_minutes": self.elapsed_minutes,
            "total_estimated_minutes": self.total_estimated_minutes,
            "phases_completed": sum(1 for p in self.phases if p.status == PhaseStatus.COMPLETED),
            "phases_total": len(self.phases),
        }
