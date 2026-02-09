"""
Sales Domain Models

DealStage pipeline, Client, Deal, SalesActivity, Quote, SalesProduct.
All data persisted via CSV (Phase 1).
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class DealStage(Enum):
    """Sales pipeline stages"""
    PROSPECTING = "prospecting"
    VALIDATION = "validation"
    PROPOSAL = "proposal"
    NEGOTIATION = "negotiation"
    CLOSED_WON = "closed_won"
    CLOSED_LOST = "closed_lost"


# Stage probability mapping
STAGE_PROBABILITY: Dict[DealStage, int] = {
    DealStage.PROSPECTING: 10,
    DealStage.VALIDATION: 30,
    DealStage.PROPOSAL: 60,
    DealStage.NEGOTIATION: 80,
    DealStage.CLOSED_WON: 100,
    DealStage.CLOSED_LOST: 0,
}


class ActivityTypeEnum(Enum):
    """Sales activity types"""
    CALL = "call"
    EMAIL = "email"
    MEETING = "meeting"
    NOTE = "note"


@dataclass
class Client:
    """CRM Client"""
    id: str
    name: str
    industry: str = ""
    tier: str = "standard"  # standard, premium, enterprise
    created_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.utcnow().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "industry": self.industry,
            "tier": self.tier,
            "created_at": self.created_at,
        }


@dataclass
class Deal:
    """Sales Deal (Opportunity)"""
    id: str
    client_id: str
    title: str
    stage: DealStage = DealStage.PROSPECTING
    amount: float = 0.0
    probability: int = -1  # -1 = auto from stage
    owner: str = "SALES"
    last_activity_at: str = ""
    stage_entered_at: str = ""
    created_at: str = ""
    final_price: Optional[float] = None
    lost_reason: Optional[str] = None
    lost_to_competitor: Optional[str] = None

    def __post_init__(self):
        now = datetime.utcnow().isoformat()
        if not self.created_at:
            self.created_at = now
        if not self.stage_entered_at:
            self.stage_entered_at = now
        if not self.last_activity_at:
            self.last_activity_at = now
        if self.probability < 0:
            self.probability = STAGE_PROBABILITY.get(self.stage, 10)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "client_id": self.client_id,
            "title": self.title,
            "stage": self.stage.value,
            "amount": self.amount,
            "probability": self.probability,
            "owner": self.owner,
            "last_activity_at": self.last_activity_at,
            "stage_entered_at": self.stage_entered_at,
            "created_at": self.created_at,
            "final_price": self.final_price,
            "lost_reason": self.lost_reason,
            "lost_to_competitor": self.lost_to_competitor,
        }


@dataclass
class SalesActivity:
    """Sales interaction record"""
    id: str
    deal_id: str
    type: ActivityTypeEnum = ActivityTypeEnum.NOTE
    summary: str = ""
    created_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.utcnow().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "deal_id": self.deal_id,
            "type": self.type.value,
            "summary": self.summary,
            "created_at": self.created_at,
        }


@dataclass
class Quote:
    """Sales quotation"""
    id: str
    deal_id: str
    version: int = 1
    total_price: float = 0.0
    margin: float = 0.0
    evidence_log: str = ""
    created_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.utcnow().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "deal_id": self.deal_id,
            "version": self.version,
            "total_price": self.total_price,
            "margin": self.margin,
            "evidence_log": self.evidence_log,
            "created_at": self.created_at,
        }


@dataclass
class SalesProduct:
    """Product catalog item with cost"""
    id: str
    name: str
    list_price: float = 0.0
    cost_base: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "list_price": self.list_price,
            "cost_base": self.cost_base,
        }
