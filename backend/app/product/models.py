"""
Product Pipeline Models

產品開發流水線資料模型
Based on docs/pipelines/product-pipeline.md
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4


class ProductStage(Enum):
    """產品開發階段"""
    P1_BACKLOG = "backlog"           # 需求池 (CEO 想法)
    P2_SPEC_READY = "spec_ready"     # 規格確認 (PM 完成)
    P3_IN_PROGRESS = "in_progress"   # 開發中 (BUILDER)
    P4_QA_TESTING = "qa_testing"     # 內部測試 (INSPECTOR)
    P5_UAT = "uat"                   # 使用者驗收 (CEO)
    P6_DONE = "done"                 # 上線完成
    BLOCKED = "blocked"              # 被阻擋


class ProductPriority(Enum):
    """優先級"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ProductType(Enum):
    """產品類型"""
    FEATURE = "feature"          # 新功能
    ENHANCEMENT = "enhancement"  # 功能增強
    BUG_FIX = "bug_fix"         # Bug 修復
    TECH_DEBT = "tech_debt"     # 技術債務
    EXPERIMENT = "experiment"    # 實驗性功能


# Stage transition order
STAGE_ORDER = [
    ProductStage.P1_BACKLOG,
    ProductStage.P2_SPEC_READY,
    ProductStage.P3_IN_PROGRESS,
    ProductStage.P4_QA_TESTING,
    ProductStage.P5_UAT,
    ProductStage.P6_DONE,
]


@dataclass
class QAResult:
    """QA 測試結果"""
    test_name: str
    passed: bool
    details: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "test_name": self.test_name,
            "passed": self.passed,
            "details": self.details,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class UATFeedback:
    """UAT 回饋"""
    feedback: str
    from_ceo: bool = True
    approved: Optional[bool] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "feedback": self.feedback,
            "from_ceo": self.from_ceo,
            "approved": self.approved,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class ProductItem:
    """產品項目"""
    id: str
    title: str
    description: str

    # 類型與優先級
    type: ProductType = ProductType.FEATURE
    priority: ProductPriority = ProductPriority.MEDIUM

    # 階段
    stage: ProductStage = ProductStage.P1_BACKLOG
    stage_entered_at: datetime = field(default_factory=datetime.utcnow)

    # 版本
    version: Optional[str] = None  # e.g., "1.0.0"
    target_release: Optional[str] = None  # 目標版本

    # 規格文件
    spec_doc: Optional[str] = None
    acceptance_criteria: List[str] = field(default_factory=list)

    # 指派
    assignee: Optional[str] = None  # BUILDER, INSPECTOR
    owner: str = "ORCHESTRATOR"

    # QA 結果
    qa_results: List[QAResult] = field(default_factory=list)

    # UAT 回饋
    uat_feedback: List[UATFeedback] = field(default_factory=list)

    # 時間
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    # 預估
    estimated_hours: Optional[float] = None
    actual_hours: Optional[float] = None

    # 阻擋資訊
    blocked_reason: Optional[str] = None
    blocked_by: Optional[str] = None  # 依賴的 ProductItem ID

    # 來源
    source_input_id: Optional[str] = None  # 來自 CEO Intake
    related_opportunity_id: Optional[str] = None  # 來自 Sales Pipeline

    # 備註
    notes: Optional[str] = None
    tags: List[str] = field(default_factory=list)

    def __post_init__(self):
        if not self.id:
            year = datetime.now().year
            self.id = f"PROD-{year}-{uuid4().hex[:4].upper()}"

    @property
    def days_in_stage(self) -> int:
        return (datetime.utcnow() - self.stage_entered_at).days

    @property
    def qa_passed(self) -> bool:
        """所有 QA 測試是否通過"""
        if not self.qa_results:
            return False
        return all(r.passed for r in self.qa_results)

    @property
    def qa_score(self) -> float:
        """QA 通過率"""
        if not self.qa_results:
            return 0.0
        passed = sum(1 for r in self.qa_results if r.passed)
        return (passed / len(self.qa_results)) * 100

    @property
    def uat_approved(self) -> bool:
        """UAT 是否通過"""
        approved_feedback = [f for f in self.uat_feedback if f.approved is True]
        return len(approved_feedback) > 0

    def can_advance_to(self, target: ProductStage) -> tuple[bool, List[str]]:
        """檢查是否可以推進到目標階段"""
        blockers = []

        if target == ProductStage.P2_SPEC_READY:
            if not self.description:
                blockers.append("需要填寫描述")

        elif target == ProductStage.P3_IN_PROGRESS:
            if not self.spec_doc:
                blockers.append("需要填寫規格文件")
            if not self.acceptance_criteria:
                blockers.append("需要定義驗收標準")

        elif target == ProductStage.P4_QA_TESTING:
            if not self.assignee:
                blockers.append("需要指派開發人員")

        elif target == ProductStage.P5_UAT:
            if not self.qa_passed:
                blockers.append("QA 測試未通過")

        elif target == ProductStage.P6_DONE:
            if not self.uat_approved:
                blockers.append("需要 CEO 驗收通過")

        return len(blockers) == 0, blockers

    def advance_stage(self) -> Optional[ProductStage]:
        """推進到下一階段"""
        if self.stage == ProductStage.BLOCKED:
            return None

        try:
            current_idx = STAGE_ORDER.index(self.stage)
            if current_idx < len(STAGE_ORDER) - 1:
                next_stage = STAGE_ORDER[current_idx + 1]
                can_advance, _ = self.can_advance_to(next_stage)
                if can_advance:
                    self.stage = next_stage
                    self.stage_entered_at = datetime.utcnow()

                    if next_stage == ProductStage.P3_IN_PROGRESS:
                        self.started_at = datetime.utcnow()
                    elif next_stage == ProductStage.P6_DONE:
                        self.completed_at = datetime.utcnow()

                    return next_stage
        except ValueError:
            pass
        return None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "type": self.type.value,
            "priority": self.priority.value,
            "stage": self.stage.value,
            "stage_entered_at": self.stage_entered_at.isoformat(),
            "days_in_stage": self.days_in_stage,
            "version": self.version,
            "target_release": self.target_release,
            "spec_doc": self.spec_doc,
            "acceptance_criteria": self.acceptance_criteria,
            "assignee": self.assignee,
            "owner": self.owner,
            "qa_results": [r.to_dict() for r in self.qa_results],
            "qa_passed": self.qa_passed,
            "qa_score": self.qa_score,
            "uat_feedback": [f.to_dict() for f in self.uat_feedback],
            "uat_approved": self.uat_approved,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "estimated_hours": self.estimated_hours,
            "actual_hours": self.actual_hours,
            "blocked_reason": self.blocked_reason,
            "blocked_by": self.blocked_by,
            "notes": self.notes,
            "tags": self.tags,
        }

    def to_summary(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "type": self.type.value,
            "priority": self.priority.value,
            "stage": self.stage.value,
            "assignee": self.assignee,
            "days_in_stage": self.days_in_stage,
            "qa_passed": self.qa_passed,
            "version": self.version,
        }
