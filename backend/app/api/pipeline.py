"""
Sales Pipeline API Endpoints

銷售管道 API
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.pipeline.models import (
    Opportunity,
    OpportunityStage,
    OpportunityStatus,
    Contact,
    ContactRole,
    Activity,
    ActivityType,
    MEDDICScore,
)
from app.pipeline.repository import PipelineRepository

router = APIRouter()

# 全域 Repository（Tracer Bullet 版本）
_repo = PipelineRepository()


# === Request Models ===

class ContactCreate(BaseModel):
    """建立聯絡人"""
    name: str
    title: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    role: str = "contact"
    notes: Optional[str] = None


class OpportunityCreate(BaseModel):
    """建立商機"""
    name: str
    company: str
    amount: Optional[float] = None
    currency: str = "TWD"
    source: str = "unknown"
    source_detail: Optional[str] = None
    expected_close: Optional[str] = None
    owner: str = "HUNTER"
    notes: Optional[str] = None
    contacts: List[ContactCreate] = []

    # 初始 MEDDIC（可選）
    pain_description: Optional[str] = None
    pain_score: int = 0


class OpportunityUpdate(BaseModel):
    """更新商機"""
    name: Optional[str] = None
    company: Optional[str] = None
    amount: Optional[float] = None
    expected_close: Optional[str] = None
    notes: Optional[str] = None
    owner: Optional[str] = None


class ActivityCreate(BaseModel):
    """建立活動"""
    type: str  # call, email, meeting, note, task
    subject: str
    occurred_at: Optional[str] = None
    duration_minutes: Optional[int] = None
    summary: Optional[str] = None
    attendees: List[str] = []
    next_action: Optional[str] = None
    next_action_due: Optional[str] = None

    # MEDDIC 更新
    meddic_updates: Optional[Dict[str, Any]] = None


class MEDDICUpdate(BaseModel):
    """更新 MEDDIC"""
    pain_score: Optional[int] = None
    pain_identified: Optional[bool] = None
    pain_description: Optional[str] = None
    champion_score: Optional[int] = None
    champion_identified: Optional[bool] = None
    eb_score: Optional[int] = None
    eb_identified: Optional[bool] = None
    eb_access_level: Optional[str] = None


class LostRequest(BaseModel):
    """標記失敗"""
    reason: Optional[str] = None


class DormantRequest(BaseModel):
    """標記休眠"""
    reason: Optional[str] = None


# === Opportunity Endpoints ===

@router.post("/opportunities", response_model=Dict[str, Any])
async def create_opportunity(request: OpportunityCreate):
    """建立商機"""
    # 建立聯絡人
    contacts = []
    for c in request.contacts:
        contact = Contact(
            id="",
            name=c.name,
            title=c.title,
            email=c.email,
            phone=c.phone,
            role=ContactRole(c.role),
            notes=c.notes,
        )
        contacts.append(contact)

    # 建立 MEDDIC
    meddic = MEDDICScore()
    if request.pain_description:
        meddic.pain_identified = True
        meddic.pain_description = request.pain_description
        meddic.pain_score = request.pain_score or 5

    # 建立商機
    opp = Opportunity(
        id="",
        name=request.name,
        company=request.company,
        amount=request.amount,
        currency=request.currency,
        source=request.source,
        source_detail=request.source_detail,
        expected_close=datetime.fromisoformat(request.expected_close) if request.expected_close else None,
        owner=request.owner,
        notes=request.notes,
        contacts=contacts,
        meddic=meddic,
    )

    # 根據聯絡人更新 MEDDIC
    for contact in contacts:
        if contact.role == ContactRole.CHAMPION:
            meddic.champion_identified = True
            meddic.champion_name = contact.name
            meddic.champion_title = contact.title
            meddic.champion_score = 5
        elif contact.role == ContactRole.ECONOMIC_BUYER:
            meddic.eb_identified = True
            meddic.eb_name = contact.name
            meddic.eb_score = 3
            meddic.eb_access_level = "identified"

    await _repo.create_opportunity(opp)
    return opp.to_dict()


@router.get("/opportunities", response_model=List[Dict[str, Any]])
async def list_opportunities(
    stage: Optional[str] = None,
    status: Optional[str] = None,
    owner: Optional[str] = None,
    limit: int = 50,
):
    """列出商機"""
    opps = await _repo.list_opportunities(
        stage=OpportunityStage(stage) if stage else None,
        status=OpportunityStatus(status) if status else None,
        owner=owner,
        limit=limit,
    )
    return [o.to_summary() for o in opps]


@router.get("/opportunities/{opp_id}", response_model=Dict[str, Any])
async def get_opportunity(opp_id: str):
    """取得商機詳情"""
    opp = await _repo.get_opportunity(opp_id)
    if not opp:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    return opp.to_dict()


@router.put("/opportunities/{opp_id}", response_model=Dict[str, Any])
async def update_opportunity(opp_id: str, request: OpportunityUpdate):
    """更新商機"""
    opp = await _repo.get_opportunity(opp_id)
    if not opp:
        raise HTTPException(status_code=404, detail="Opportunity not found")

    if request.name:
        opp.name = request.name
    if request.company:
        opp.company = request.company
    if request.amount is not None:
        opp.amount = request.amount
    if request.expected_close:
        opp.expected_close = datetime.fromisoformat(request.expected_close)
    if request.notes:
        opp.notes = request.notes
    if request.owner:
        opp.owner = request.owner

    await _repo.update_opportunity(opp)
    return opp.to_dict()


@router.delete("/opportunities/{opp_id}")
async def delete_opportunity(opp_id: str):
    """刪除商機"""
    success = await _repo.delete_opportunity(opp_id)
    if not success:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    return {"message": f"Opportunity {opp_id} deleted"}


# === Stage Operations ===

@router.post("/opportunities/{opp_id}/advance", response_model=Dict[str, Any])
async def advance_stage(opp_id: str):
    """推進到下一階段"""
    opp = await _repo.get_opportunity(opp_id)
    if not opp:
        raise HTTPException(status_code=404, detail="Opportunity not found")

    # 檢查是否可以推進
    from app.pipeline.models import STAGE_ORDER
    current_idx = STAGE_ORDER.index(opp.stage) if opp.stage in STAGE_ORDER else -1
    if current_idx < 0 or current_idx >= len(STAGE_ORDER) - 1:
        raise HTTPException(status_code=400, detail="Cannot advance from current stage")

    next_stage = STAGE_ORDER[current_idx + 1]
    can_advance, blockers = opp.can_advance_to(next_stage)

    if not can_advance:
        raise HTTPException(
            status_code=400,
            detail={
                "message": "Cannot advance to next stage",
                "blockers": blockers,
            }
        )

    result = await _repo.advance_stage(opp_id)
    return result.to_dict()


@router.post("/opportunities/{opp_id}/stage/{stage}", response_model=Dict[str, Any])
async def set_stage(opp_id: str, stage: str):
    """設定階段"""
    try:
        target_stage = OpportunityStage(stage)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid stage: {stage}")

    result = await _repo.set_stage(opp_id, target_stage)
    if not result:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    return result.to_dict()


@router.post("/opportunities/{opp_id}/win", response_model=Dict[str, Any])
async def mark_won(opp_id: str):
    """標記成交"""
    result = await _repo.mark_won(opp_id)
    if not result:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    return result.to_dict()


@router.post("/opportunities/{opp_id}/lose", response_model=Dict[str, Any])
async def mark_lost(opp_id: str, request: LostRequest):
    """標記失敗"""
    result = await _repo.mark_lost(opp_id, request.reason)
    if not result:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    return result.to_dict()


@router.post("/opportunities/{opp_id}/dormant", response_model=Dict[str, Any])
async def mark_dormant(opp_id: str, request: DormantRequest):
    """標記休眠"""
    result = await _repo.mark_dormant(opp_id, request.reason)
    if not result:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    return result.to_dict()


@router.post("/opportunities/{opp_id}/reactivate", response_model=Dict[str, Any])
async def reactivate_opportunity(opp_id: str):
    """重新啟動休眠商機"""
    result = await _repo.reactivate(opp_id)
    if not result:
        raise HTTPException(status_code=400, detail="Cannot reactivate: opportunity not found or not dormant")
    return result.to_dict()


# === Closed Deals Endpoints ===

@router.get("/closed", response_model=List[Dict[str, Any]])
async def list_closed_deals(
    status: Optional[str] = None,
    limit: int = 100,
):
    """列出已關閉的商機 (Won/Lost/Dormant)"""
    status_enum = None
    if status:
        try:
            status_enum = OpportunityStatus(status)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status}")

    opps = await _repo.list_closed_opportunities(status=status_enum, limit=limit)
    return [o.to_summary() for o in opps]


@router.get("/closed/won", response_model=List[Dict[str, Any]])
async def list_won_deals(limit: int = 100):
    """列出成交商機"""
    opps = await _repo.list_closed_opportunities(status=OpportunityStatus.WON, limit=limit)
    return [o.to_summary() for o in opps]


@router.get("/closed/lost", response_model=List[Dict[str, Any]])
async def list_lost_deals(limit: int = 100):
    """列出失敗商機"""
    opps = await _repo.list_closed_opportunities(status=OpportunityStatus.LOST, limit=limit)
    return [o.to_summary() for o in opps]


@router.get("/closed/dormant", response_model=List[Dict[str, Any]])
async def list_dormant_deals(limit: int = 100):
    """列出休眠商機"""
    opps = await _repo.list_closed_opportunities(status=OpportunityStatus.DORMANT, limit=limit)
    return [o.to_summary() for o in opps]


# === Contact Endpoints ===

@router.post("/opportunities/{opp_id}/contacts", response_model=Dict[str, Any])
async def add_contact(opp_id: str, request: ContactCreate):
    """新增聯絡人"""
    contact = Contact(
        id="",
        name=request.name,
        title=request.title,
        email=request.email,
        phone=request.phone,
        role=ContactRole(request.role),
        notes=request.notes,
    )

    result = await _repo.add_contact(opp_id, contact)
    if not result:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    return result.to_dict()


@router.get("/opportunities/{opp_id}/contacts", response_model=List[Dict[str, Any]])
async def list_contacts(opp_id: str):
    """列出聯絡人"""
    opp = await _repo.get_opportunity(opp_id)
    if not opp:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    return [c.to_dict() for c in opp.contacts]


# === Activity Endpoints ===

@router.post("/opportunities/{opp_id}/activities", response_model=Dict[str, Any])
async def add_activity(opp_id: str, request: ActivityCreate):
    """新增活動"""
    opp = await _repo.get_opportunity(opp_id)
    if not opp:
        raise HTTPException(status_code=404, detail="Opportunity not found")

    activity = Activity(
        id="",
        opportunity_id=opp_id,
        type=ActivityType(request.type),
        subject=request.subject,
        occurred_at=datetime.fromisoformat(request.occurred_at) if request.occurred_at else datetime.utcnow(),
        duration_minutes=request.duration_minutes,
        summary=request.summary,
        attendees=request.attendees,
        next_action=request.next_action,
        next_action_due=datetime.fromisoformat(request.next_action_due) if request.next_action_due else None,
        meddic_updates=request.meddic_updates,
    )

    await _repo.add_activity(activity)

    # 如果有 MEDDIC 更新
    if request.meddic_updates:
        await _repo.update_meddic(opp_id, request.meddic_updates)

    return activity.to_dict()


@router.get("/opportunities/{opp_id}/activities", response_model=List[Dict[str, Any]])
async def list_activities(opp_id: str, limit: int = 20):
    """列出活動"""
    activities = await _repo.get_activities(opp_id, limit)
    return [a.to_dict() for a in activities]


# === MEDDIC Endpoints ===

@router.get("/opportunities/{opp_id}/meddic", response_model=Dict[str, Any])
async def get_meddic(opp_id: str):
    """取得 MEDDIC 分析"""
    opp = await _repo.get_opportunity(opp_id)
    if not opp:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    return opp.meddic.to_dict()


@router.put("/opportunities/{opp_id}/meddic", response_model=Dict[str, Any])
async def update_meddic(opp_id: str, request: MEDDICUpdate):
    """更新 MEDDIC"""
    updates = request.model_dump(exclude_none=True)
    result = await _repo.update_meddic(opp_id, updates)
    if not result:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    return result.to_dict()


# === Dashboard Endpoints ===

@router.get("/dashboard", response_model=Dict[str, Any])
async def get_dashboard():
    """取得 Pipeline 儀表板"""
    return _repo.get_pipeline_summary()


@router.get("/statistics", response_model=Dict[str, Any])
async def get_statistics():
    """取得統計資訊"""
    return _repo.get_statistics()
