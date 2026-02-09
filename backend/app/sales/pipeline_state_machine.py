"""
Sales Pipeline State Machine

Valid stage transitions, deal validation, stagnation detection.
"""

from datetime import datetime
from typing import Dict, List, Optional, Tuple

from app.sales.models import Deal, DealStage, STAGE_PROBABILITY


# Valid transitions: key = current stage, value = allowed next stages
VALID_TRANSITIONS: Dict[DealStage, List[DealStage]] = {
    DealStage.PROSPECTING: [DealStage.VALIDATION, DealStage.CLOSED_LOST],
    DealStage.VALIDATION: [DealStage.PROPOSAL, DealStage.CLOSED_LOST],
    DealStage.PROPOSAL: [DealStage.NEGOTIATION, DealStage.CLOSED_LOST],
    DealStage.NEGOTIATION: [DealStage.CLOSED_WON, DealStage.CLOSED_LOST],
    DealStage.CLOSED_WON: [],
    DealStage.CLOSED_LOST: [],
}

# Stagnation thresholds (days per stage)
STAGNATION_THRESHOLDS: Dict[DealStage, int] = {
    DealStage.PROSPECTING: 7,
    DealStage.VALIDATION: 10,
    DealStage.PROPOSAL: 14,
    DealStage.NEGOTIATION: 10,
}


class NewDealValidationError(Exception):
    """Raised when a new deal fails validation."""
    def __init__(self, missing_fields: List[str]):
        self.missing_fields = missing_fields
        super().__init__(f"Missing required fields: {', '.join(missing_fields)}")


def validate_new_deal(
    client_name: Optional[str],
    amount: Optional[float],
    next_action: Optional[str],
) -> List[str]:
    """
    Module A Gatekeeper: validate a new deal before creation.

    Returns list of missing fields (empty = valid).
    """
    missing = []
    if not client_name or not client_name.strip():
        missing.append("client_name")
    if amount is None or amount <= 0:
        missing.append("amount")
    if not next_action or not next_action.strip():
        missing.append("next_action")
    return missing


def can_transition(current: DealStage, target: DealStage) -> Tuple[bool, str]:
    """
    Check if a stage transition is valid.

    Returns (ok, reason).
    """
    if current == target:
        return False, "Already in this stage"

    allowed = VALID_TRANSITIONS.get(current, [])
    if target not in allowed:
        allowed_names = [s.value for s in allowed]
        return False, f"Cannot transition from {current.value} to {target.value}. Allowed: {allowed_names}"

    return True, "OK"


def advance_deal(deal: Deal, target: DealStage) -> Tuple[bool, str]:
    """
    Advance a deal to the target stage.

    Mutates the deal in place:
    - Updates stage + probability
    - Resets stage_entered_at

    Returns (ok, reason).
    """
    ok, reason = can_transition(deal.stage, target)
    if not ok:
        return False, reason

    now = datetime.utcnow().isoformat()
    deal.stage = target
    deal.probability = STAGE_PROBABILITY.get(target, deal.probability)
    deal.stage_entered_at = now
    deal.last_activity_at = now
    return True, "OK"


def close_won(deal: Deal, final_price: Optional[float] = None) -> Tuple[bool, str]:
    """Close a deal as won."""
    ok, reason = can_transition(deal.stage, DealStage.CLOSED_WON)
    if not ok:
        return False, reason

    now = datetime.utcnow().isoformat()
    deal.stage = DealStage.CLOSED_WON
    deal.probability = 100
    deal.stage_entered_at = now
    deal.last_activity_at = now
    deal.final_price = final_price if final_price is not None else deal.amount
    return True, "OK"


def close_lost(
    deal: Deal,
    reason: Optional[str] = None,
    competitor: Optional[str] = None,
) -> Tuple[bool, str]:
    """Close a deal as lost."""
    allowed = VALID_TRANSITIONS.get(deal.stage, [])
    if DealStage.CLOSED_LOST not in allowed:
        return False, f"Cannot close-lost from {deal.stage.value}"

    now = datetime.utcnow().isoformat()
    deal.stage = DealStage.CLOSED_LOST
    deal.probability = 0
    deal.stage_entered_at = now
    deal.last_activity_at = now
    deal.lost_reason = reason
    deal.lost_to_competitor = competitor
    return True, "OK"


def days_in_current_stage(deal: Deal) -> int:
    """Calculate days the deal has been in its current stage."""
    if not deal.stage_entered_at:
        return 0
    try:
        entered = datetime.fromisoformat(deal.stage_entered_at)
        return (datetime.utcnow() - entered).days
    except (ValueError, TypeError):
        return 0


def is_stagnant(deal: Deal) -> bool:
    """Check if a deal is stagnant (over threshold for its stage)."""
    threshold = STAGNATION_THRESHOLDS.get(deal.stage)
    if threshold is None:
        return False  # closed stages don't stagnate
    return days_in_current_stage(deal) > threshold


def detect_stagnant_deals(deals: List[Deal]) -> List[Dict]:
    """
    Return list of stagnant deal summaries for daily briefing.
    """
    stagnant = []
    for deal in deals:
        if deal.stage in (DealStage.CLOSED_WON, DealStage.CLOSED_LOST):
            continue
        if is_stagnant(deal):
            days = days_in_current_stage(deal)
            threshold = STAGNATION_THRESHOLDS.get(deal.stage, 0)
            stagnant.append({
                "deal_id": deal.id,
                "title": deal.title,
                "stage": deal.stage.value,
                "days_in_stage": days,
                "threshold": threshold,
                "overdue_days": days - threshold,
            })
    return stagnant
