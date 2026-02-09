"""
Sales API Endpoints

REST API for sales pipeline: deals, clients, activities, quotes, dashboard.
"""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.sales.csv_repository import get_sales_repo
from app.sales.models import (
    ActivityTypeEnum,
    Client,
    Deal,
    DealStage,
    SalesActivity,
)
from app.sales.pipeline_state_machine import (
    advance_deal,
    close_lost,
    close_won,
)

router = APIRouter()


# === Request Models ===

class CreateDealRequest(BaseModel):
    client_id: str
    title: str
    amount: float = 0.0
    owner: str = "SALES"


class CreateClientRequest(BaseModel):
    name: str
    industry: str = ""
    tier: str = "standard"


class AdvanceStageRequest(BaseModel):
    target_stage: Optional[str] = None  # if None, auto-advance to next


class CloseWonRequest(BaseModel):
    final_price: Optional[float] = None


class CloseLostRequest(BaseModel):
    reason: Optional[str] = None
    competitor: Optional[str] = None


class CreateActivityRequest(BaseModel):
    type: str = "note"  # call, email, meeting, note
    summary: str = ""


class GenerateQuoteRequest(BaseModel):
    product_ids: List[str] = []
    margin_pct: float = 30.0


# === Deals ===

@router.post("/deals", response_model=Dict[str, Any])
async def create_deal(request: CreateDealRequest):
    """Create a new deal."""
    repo = get_sales_repo()

    # Verify client exists
    client = await repo.get_client(request.client_id)
    if not client:
        raise HTTPException(status_code=404, detail=f"Client {request.client_id} not found")

    deal = Deal(
        id="",
        client_id=request.client_id,
        title=request.title,
        amount=request.amount,
        owner=request.owner,
    )
    deal = await repo.create_deal(deal)
    return deal.to_dict()


@router.get("/deals", response_model=List[Dict[str, Any]])
async def list_deals(
    stage: Optional[str] = None,
    client_id: Optional[str] = None,
):
    """List deals with optional filters."""
    repo = get_sales_repo()

    stage_enum = None
    if stage:
        try:
            stage_enum = DealStage(stage)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid stage: {stage}")

    deals = await repo.list_deals(stage=stage_enum, client_id=client_id)
    return [d.to_dict() for d in deals]


@router.get("/deals/{deal_id}", response_model=Dict[str, Any])
async def get_deal(deal_id: str):
    """Get deal detail."""
    repo = get_sales_repo()
    deal = await repo.get_deal(deal_id)
    if not deal:
        raise HTTPException(status_code=404, detail=f"Deal {deal_id} not found")
    return deal.to_dict()


@router.post("/deals/{deal_id}/advance", response_model=Dict[str, Any])
async def advance_deal_stage(deal_id: str, request: AdvanceStageRequest):
    """Advance deal to next stage (or specified target)."""
    repo = get_sales_repo()
    deal = await repo.get_deal(deal_id)
    if not deal:
        raise HTTPException(status_code=404, detail=f"Deal {deal_id} not found")

    # Determine target
    if request.target_stage:
        try:
            target = DealStage(request.target_stage)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid stage: {request.target_stage}")
        # Terminal stages have dedicated endpoints
        if target in (DealStage.CLOSED_WON, DealStage.CLOSED_LOST):
            raise HTTPException(status_code=400, detail=f"Use /close-won or /close-lost endpoint for terminal stages")
    else:
        # Auto-advance: next in sequence (excludes terminal stages)
        stage_order = [
            DealStage.PROSPECTING,
            DealStage.VALIDATION,
            DealStage.PROPOSAL,
            DealStage.NEGOTIATION,
        ]
        try:
            idx = stage_order.index(deal.stage)
            if idx + 1 >= len(stage_order):
                raise HTTPException(status_code=400, detail="Already at final active stage. Use /close-won or /close-lost")
            target = stage_order[idx + 1]
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Cannot advance from {deal.stage.value}")

    ok, reason = advance_deal(deal, target)
    if not ok:
        raise HTTPException(status_code=400, detail=reason)

    await repo.update_deal(deal)

    # Log activity
    await repo.create_activity(SalesActivity(
        id="",
        deal_id=deal.id,
        type=ActivityTypeEnum.NOTE,
        summary=f"Stage advanced to {target.value}",
    ))

    return {"status": "advanced", "deal": deal.to_dict()}


@router.post("/deals/{deal_id}/close-won", response_model=Dict[str, Any])
async def close_deal_won(deal_id: str, request: CloseWonRequest):
    """Close deal as won."""
    repo = get_sales_repo()
    deal = await repo.get_deal(deal_id)
    if not deal:
        raise HTTPException(status_code=404, detail=f"Deal {deal_id} not found")

    ok, reason = close_won(deal, final_price=request.final_price)
    if not ok:
        raise HTTPException(status_code=400, detail=reason)

    await repo.update_deal(deal)

    await repo.create_activity(SalesActivity(
        id="",
        deal_id=deal.id,
        type=ActivityTypeEnum.NOTE,
        summary=f"Deal closed won. Final price: {deal.final_price}",
    ))

    return {"status": "won", "deal": deal.to_dict()}


@router.post("/deals/{deal_id}/close-lost", response_model=Dict[str, Any])
async def close_deal_lost(deal_id: str, request: CloseLostRequest):
    """Close deal as lost."""
    repo = get_sales_repo()
    deal = await repo.get_deal(deal_id)
    if not deal:
        raise HTTPException(status_code=404, detail=f"Deal {deal_id} not found")

    ok, reason = close_lost(deal, reason=request.reason, competitor=request.competitor)
    if not ok:
        raise HTTPException(status_code=400, detail=reason)

    await repo.update_deal(deal)

    await repo.create_activity(SalesActivity(
        id="",
        deal_id=deal.id,
        type=ActivityTypeEnum.NOTE,
        summary=f"Deal closed lost. Reason: {request.reason or 'N/A'}",
    ))

    return {"status": "lost", "deal": deal.to_dict()}


# === Activities ===

@router.post("/deals/{deal_id}/activities", response_model=Dict[str, Any])
async def create_activity(deal_id: str, request: CreateActivityRequest):
    """Log a sales activity for a deal."""
    repo = get_sales_repo()
    deal = await repo.get_deal(deal_id)
    if not deal:
        raise HTTPException(status_code=404, detail=f"Deal {deal_id} not found")

    try:
        activity_type = ActivityTypeEnum(request.type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid activity type: {request.type}")

    activity = SalesActivity(
        id="",
        deal_id=deal_id,
        type=activity_type,
        summary=request.summary,
    )
    activity = await repo.create_activity(activity)
    return activity.to_dict()


@router.get("/deals/{deal_id}/activities", response_model=List[Dict[str, Any]])
async def list_activities(deal_id: str):
    """List activities for a deal."""
    repo = get_sales_repo()
    deal = await repo.get_deal(deal_id)
    if not deal:
        raise HTTPException(status_code=404, detail=f"Deal {deal_id} not found")

    activities = await repo.list_activities(deal_id=deal_id)
    return [a.to_dict() for a in activities]


# === Clients ===

@router.get("/clients", response_model=List[Dict[str, Any]])
async def list_clients():
    """List all clients."""
    repo = get_sales_repo()
    clients = await repo.list_clients()
    return [c.to_dict() for c in clients]


@router.post("/clients", response_model=Dict[str, Any])
async def create_client(request: CreateClientRequest):
    """Create a new client."""
    repo = get_sales_repo()
    client = Client(
        id="",
        name=request.name,
        industry=request.industry,
        tier=request.tier,
    )
    client = await repo.create_client(client)
    return client.to_dict()


# === Dashboard & Briefing ===

@router.get("/dashboard", response_model=Dict[str, Any])
async def get_dashboard():
    """Pipeline summary dashboard."""
    repo = get_sales_repo()
    return await repo.get_pipeline_summary()


@router.get("/daily-briefing", response_model=Dict[str, Any])
async def get_daily_briefing():
    """Daily briefing: stagnation alerts + pipeline summary."""
    from app.agents.sales import get_sales_agent
    agent = get_sales_agent()
    return await agent.handle({"action": "daily_briefing"})


# === Products ===

@router.get("/products", response_model=List[Dict[str, Any]])
async def list_products():
    """List product catalog."""
    repo = get_sales_repo()
    products = await repo.list_products()
    return [p.to_dict() for p in products]


# === Quotes ===

@router.post("/deals/{deal_id}/quotes", response_model=Dict[str, Any])
async def generate_quote(deal_id: str, request: GenerateQuoteRequest):
    """Generate a cost-plus quote for a deal."""
    from app.agents.sales import get_sales_agent
    agent = get_sales_agent()
    return await agent.handle({
        "action": "generate_quote",
        "deal_id": deal_id,
        "product_ids": request.product_ids,
        "margin_pct": request.margin_pct,
    })


@router.get("/deals/{deal_id}/quotes", response_model=List[Dict[str, Any]])
async def list_quotes(deal_id: str):
    """List quotes for a deal."""
    repo = get_sales_repo()
    quotes = await repo.list_quotes(deal_id=deal_id)
    return [q.to_dict() for q in quotes]
