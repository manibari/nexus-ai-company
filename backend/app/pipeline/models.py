"""
Sales Pipeline Models

銷售管道資料模型
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4


class OpportunityStage(Enum):
    """銷售階段"""
    LEAD = "lead"                    # 新線索 (10%)
    QUALIFICATION = "qualification"  # 資格確認 (20%)
    DISCOVERY = "discovery"          # 需求探索 (40%)
    PROPOSAL = "proposal"            # 提案報價 (70%)
    NEGOTIATION = "negotiation"      # 議價協商 (85%)
    WON = "won"                      # 成交 (100%)
    LOST = "lost"                    # 失敗 (0%)
    DORMANT = "dormant"              # 休眠


class OpportunityStatus(Enum):
    """商機狀態"""
    OPEN = "open"
    WON = "won"
    LOST = "lost"
    DORMANT = "dormant"


class ContactRole(Enum):
    """聯絡人角色"""
    CHAMPION = "champion"
    ECONOMIC_BUYER = "economic_buyer"
    INFLUENCER = "influencer"
    BLOCKER = "blocker"
    USER = "user"
    CONTACT = "contact"


class ActivityType(Enum):
    """活動類型"""
    CALL = "call"
    EMAIL = "email"
    MEETING = "meeting"
    NOTE = "note"
    TASK = "task"


# 階段對應的成交機率
STAGE_PROBABILITIES = {
    OpportunityStage.LEAD: 0.10,
    OpportunityStage.QUALIFICATION: 0.20,
    OpportunityStage.DISCOVERY: 0.40,
    OpportunityStage.PROPOSAL: 0.70,
    OpportunityStage.NEGOTIATION: 0.85,
    OpportunityStage.WON: 1.0,
    OpportunityStage.LOST: 0.0,
    OpportunityStage.DORMANT: 0.05,
}

# 階段順序
STAGE_ORDER = [
    OpportunityStage.LEAD,
    OpportunityStage.QUALIFICATION,
    OpportunityStage.DISCOVERY,
    OpportunityStage.PROPOSAL,
    OpportunityStage.NEGOTIATION,
    OpportunityStage.WON,
]


@dataclass
class Contact:
    """聯絡人"""
    id: str
    name: str
    title: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    role: ContactRole = ContactRole.CONTACT
    notes: Optional[str] = None

    def __post_init__(self):
        if not self.id:
            self.id = f"CON-{uuid4().hex[:8].upper()}"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "title": self.title,
            "email": self.email,
            "phone": self.phone,
            "role": self.role.value,
            "notes": self.notes,
        }


@dataclass
class Activity:
    """活動/互動紀錄"""
    id: str
    opportunity_id: str
    type: ActivityType
    subject: str

    occurred_at: datetime = field(default_factory=datetime.utcnow)
    duration_minutes: Optional[int] = None

    summary: Optional[str] = None
    attendees: List[str] = field(default_factory=list)

    # 下一步
    next_action: Optional[str] = None
    next_action_due: Optional[datetime] = None

    # MEDDIC 更新（如果有）
    meddic_updates: Optional[Dict[str, Any]] = None

    created_by: str = "HUNTER"
    created_at: datetime = field(default_factory=datetime.utcnow)

    def __post_init__(self):
        if not self.id:
            self.id = f"ACT-{uuid4().hex[:8].upper()}"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "opportunity_id": self.opportunity_id,
            "type": self.type.value,
            "subject": self.subject,
            "occurred_at": self.occurred_at.isoformat(),
            "duration_minutes": self.duration_minutes,
            "summary": self.summary,
            "attendees": self.attendees,
            "next_action": self.next_action,
            "next_action_due": self.next_action_due.isoformat() if self.next_action_due else None,
            "meddic_updates": self.meddic_updates,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class MEDDICScore:
    """MEDDIC 分數快照"""
    pain_score: int = 0
    pain_identified: bool = False
    pain_description: Optional[str] = None

    champion_score: int = 0
    champion_identified: bool = False
    champion_name: Optional[str] = None
    champion_title: Optional[str] = None

    eb_score: int = 0
    eb_identified: bool = False
    eb_name: Optional[str] = None
    eb_access_level: str = "unknown"

    @property
    def total_score(self) -> int:
        """總分 0-100"""
        # Pain: 30%, Champion: 35%, EB: 35%
        pain = self.pain_score * 3  # max 30
        champion = int(self.champion_score * 3.5)  # max ~31
        eb = int(self.eb_score * 3.5)  # max 35
        return min(100, pain + champion + eb)

    @property
    def health(self) -> str:
        """Deal 健康度"""
        score = self.total_score
        if score >= 70:
            return "healthy"
        elif score >= 50:
            return "at_risk"
        elif score >= 30:
            return "needs_attention"
        else:
            return "weak"

    def get_gaps(self) -> List[str]:
        """找出缺口"""
        gaps = []
        if not self.pain_identified:
            gaps.append("痛點未確認")
        elif self.pain_score < 6:
            gaps.append("痛點強度不足")
        if not self.champion_identified:
            gaps.append("尚未找到 Champion")
        elif self.champion_score < 6:
            gaps.append("Champion 影響力不足")
        if not self.eb_identified:
            gaps.append("Economic Buyer 未確認")
        elif self.eb_access_level in ["unknown", "identified"]:
            gaps.append("尚未接觸 Economic Buyer")
        return gaps

    def get_next_actions(self) -> List[str]:
        """建議下一步"""
        actions = []
        gaps = self.get_gaps()

        if "痛點未確認" in gaps:
            actions.append("進行 Discovery Call 了解客戶痛點")
        if "痛點強度不足" in gaps:
            actions.append("量化痛點的商業影響")
        if "尚未找到 Champion" in gaps:
            actions.append("識別並培養內部支持者")
        if "Champion 影響力不足" in gaps:
            actions.append("尋找更高層級的支持者")
        if "Economic Buyer 未確認" in gaps:
            actions.append("向 Champion 確認決策者是誰")
        if "尚未接觸 Economic Buyer" in gaps:
            actions.append("透過 Champion 安排與決策者會議")

        if not actions:
            actions.append("持續推進，準備提案")

        return actions

    def to_dict(self) -> Dict[str, Any]:
        return {
            "pain": {
                "score": self.pain_score,
                "identified": self.pain_identified,
                "description": self.pain_description,
            },
            "champion": {
                "score": self.champion_score,
                "identified": self.champion_identified,
                "name": self.champion_name,
                "title": self.champion_title,
            },
            "economic_buyer": {
                "score": self.eb_score,
                "identified": self.eb_identified,
                "name": self.eb_name,
                "access_level": self.eb_access_level,
            },
            "total_score": self.total_score,
            "health": self.health,
            "gaps": self.get_gaps(),
            "next_actions": self.get_next_actions(),
        }


@dataclass
class Opportunity:
    """商機"""
    id: str
    name: str
    company: str

    # 金額
    amount: Optional[float] = None
    currency: str = "TWD"

    # 階段
    stage: OpportunityStage = OpportunityStage.LEAD
    stage_entered_at: datetime = field(default_factory=datetime.utcnow)

    # MEDDIC
    meddic: MEDDICScore = field(default_factory=MEDDICScore)

    # 聯絡人
    contacts: List[Contact] = field(default_factory=list)

    # 時間
    created_at: datetime = field(default_factory=datetime.utcnow)
    expected_close: Optional[datetime] = None
    last_activity_at: Optional[datetime] = None

    # 來源
    source: str = "unknown"
    source_detail: Optional[str] = None
    source_input_id: Optional[str] = None

    # 負責
    owner: str = "HUNTER"

    # 狀態
    status: OpportunityStatus = OpportunityStatus.OPEN

    # 失敗原因
    lost_reason: Optional[str] = None

    # 備註
    notes: Optional[str] = None

    # 關聯 Goal（成交後）
    related_goal_id: Optional[str] = None

    def __post_init__(self):
        if not self.id:
            self.id = f"OPP-{datetime.now().strftime('%Y%m%d')}-{uuid4().hex[:4].upper()}"

    @property
    def days_in_stage(self) -> int:
        """在當前階段的天數"""
        return (datetime.utcnow() - self.stage_entered_at).days

    @property
    def days_since_activity(self) -> Optional[int]:
        """距離上次活動的天數"""
        if self.last_activity_at:
            return (datetime.utcnow() - self.last_activity_at).days
        return None

    @property
    def is_stale(self) -> bool:
        """超過 14 天沒有活動"""
        days = self.days_since_activity
        return days is not None and days > 14

    @property
    def win_probability(self) -> float:
        """成交機率"""
        return STAGE_PROBABILITIES.get(self.stage, 0.0)

    @property
    def weighted_amount(self) -> float:
        """加權金額"""
        if self.amount:
            return self.amount * self.win_probability
        return 0.0

    @property
    def champion(self) -> Optional[Contact]:
        """取得 Champion"""
        for contact in self.contacts:
            if contact.role == ContactRole.CHAMPION:
                return contact
        return None

    @property
    def economic_buyer(self) -> Optional[Contact]:
        """取得 Economic Buyer"""
        for contact in self.contacts:
            if contact.role == ContactRole.ECONOMIC_BUYER:
                return contact
        return None

    def can_advance_to(self, target_stage: OpportunityStage) -> tuple[bool, List[str]]:
        """檢查是否可以推進到目標階段"""
        blockers = []

        if target_stage == OpportunityStage.QUALIFICATION:
            if not self.meddic.pain_identified:
                blockers.append("需要先確認客戶痛點")

        elif target_stage == OpportunityStage.DISCOVERY:
            if not self.meddic.champion_identified:
                blockers.append("需要先找到 Champion")

        elif target_stage == OpportunityStage.PROPOSAL:
            if self.meddic.eb_access_level not in ["meeting", "committed"]:
                blockers.append("需要先與 Economic Buyer 會面")

        elif target_stage == OpportunityStage.NEGOTIATION:
            if self.meddic.total_score < 60:
                blockers.append("MEDDIC 分數需達 60 分以上")

        elif target_stage == OpportunityStage.WON:
            if self.meddic.total_score < 70:
                blockers.append("MEDDIC 分數需達 70 分以上")

        return len(blockers) == 0, blockers

    def advance_stage(self) -> Optional[OpportunityStage]:
        """推進到下一階段"""
        current_index = STAGE_ORDER.index(self.stage) if self.stage in STAGE_ORDER else -1
        if current_index >= 0 and current_index < len(STAGE_ORDER) - 1:
            next_stage = STAGE_ORDER[current_index + 1]
            can_advance, _ = self.can_advance_to(next_stage)
            if can_advance:
                self.stage = next_stage
                self.stage_entered_at = datetime.utcnow()
                if next_stage == OpportunityStage.WON:
                    self.status = OpportunityStatus.WON
                return next_stage
        return None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "company": self.company,
            "amount": self.amount,
            "currency": self.currency,
            "stage": self.stage.value,
            "stage_entered_at": self.stage_entered_at.isoformat(),
            "days_in_stage": self.days_in_stage,
            "meddic": self.meddic.to_dict(),
            "contacts": [c.to_dict() for c in self.contacts],
            "champion": self.champion.to_dict() if self.champion else None,
            "economic_buyer": self.economic_buyer.to_dict() if self.economic_buyer else None,
            "created_at": self.created_at.isoformat(),
            "expected_close": self.expected_close.isoformat() if self.expected_close else None,
            "last_activity_at": self.last_activity_at.isoformat() if self.last_activity_at else None,
            "days_since_activity": self.days_since_activity,
            "is_stale": self.is_stale,
            "source": self.source,
            "source_detail": self.source_detail,
            "owner": self.owner,
            "status": self.status.value,
            "win_probability": self.win_probability,
            "weighted_amount": self.weighted_amount,
            "lost_reason": self.lost_reason,
            "notes": self.notes,
            "related_goal_id": self.related_goal_id,
        }

    def to_summary(self) -> Dict[str, Any]:
        """簡化摘要"""
        return {
            "id": self.id,
            "name": self.name,
            "company": self.company,
            "amount": self.amount,
            "stage": self.stage.value,
            "status": self.status.value,
            "meddic_score": self.meddic.total_score,
            "meddic_health": self.meddic.health,
            "win_probability": self.win_probability,
            "weighted_amount": self.weighted_amount,
            "days_in_stage": self.days_in_stage,
            "is_stale": self.is_stale,
            "champion": self.champion.name if self.champion else None,
            "expected_close": self.expected_close.isoformat() if self.expected_close else None,
        }
