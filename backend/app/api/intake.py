"""
CEO Intake API Endpoints

接收和處理 CEO 的非結構化輸入
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.agents.activity_log import ActivityType, get_activity_repo

router = APIRouter()


# === Request/Response Models ===

class CEOInputRequest(BaseModel):
    """CEO 輸入請求"""
    content: str
    input_type: str = "text"  # text, email, url, voice, image
    source: str = "web"       # web, slack, email, api
    attachments: List[str] = []
    metadata: Dict[str, Any] = {}


class CEOInputResponse(BaseModel):
    """CEO 輸入回應"""
    id: str
    status: str
    intent: str
    confidence: float
    summary: str
    suggested_actions: List[str]
    requires_confirmation: bool
    created_at: str


class ConfirmationRequest(BaseModel):
    """確認請求"""
    confirmed: bool
    feedback: Optional[str] = None
    modifications: Optional[Dict[str, Any]] = None


class IntakeSummary(BaseModel):
    """輸入摘要"""
    total: int
    pending: int
    awaiting_confirmation: int
    completed: int
    by_intent: Dict[str, int]


# === Endpoints ===

@router.post("/input", response_model=CEOInputResponse)
async def receive_ceo_input(request: CEOInputRequest):
    """
    接收 CEO 輸入

    使用 GATEKEEPER Agent (Gemini 2.5 Flash) 進行：
    1. 意圖識別
    2. 實體解析
    3. 路由決策
    4. 建議動作

    根據意圖自動分派：
    - product_feature → PM Agent
    - opportunity → HUNTER Agent
    - 其他 → 待確認
    """
    from uuid import uuid4
    from app.agents.gatekeeper import GatekeeperAgent, Intent

    input_id = str(uuid4())

    # 記錄 CEO 活動
    activity_repo = get_activity_repo()
    await activity_repo.log(
        agent_id="CEO",
        agent_name="CEO",
        activity_type=ActivityType.MESSAGE,
        message=f"下達指令: {request.content[:80]}{'...' if len(request.content) > 80 else ''}",
        metadata={
            "input_id": input_id,
            "source": request.source,
            "input_type": request.input_type,
        },
    )

    # 使用 GATEKEEPER 分析
    gatekeeper = GatekeeperAgent()
    analysis = await gatekeeper.analyze(request.content, source=request.source)

    # 根據意圖生成摘要
    intent_labels = {
        "product_feature": "產品功能需求",
        "product_bug": "產品 Bug",
        "opportunity": "商機線索",
        "project_status": "專案狀態查詢",
        "project": "新專案需求",
        "task": "任務",
        "question": "問題",
        "info": "資訊記錄",
    }
    intent_label = intent_labels.get(analysis.intent.value, analysis.intent.value)

    # 根據意圖分派到對應 Agent
    extra_data = {}

    if analysis.intent == Intent.PRODUCT_FEATURE:
        # 自動轉給 PM Agent 處理
        from app.agents.pm import get_pm_agent
        pm = get_pm_agent()
        entities = [{"entity_type": e.entity_type, "value": e.value} for e in analysis.entities]
        pm_result = await pm.process_feature_request(
            content=request.content,
            entities=entities,
            intake_id=input_id,
        )
        extra_data = {
            "feature_id": pm_result.get("feature", {}).get("id"),
            "prd_summary": pm_result.get("prd", {}).get("summary"),
            "routed_to": "PM",
        }
        summary = f"識別為【{intent_label}】\n{pm_result.get('prd', {}).get('summary', analysis.summary)}"
        suggested_actions = [
            f"功能需求 {extra_data.get('feature_id')} 已建立",
            "PM 已撰寫 PRD，待 CEO 確認",
            "確認後將分派給 DEVELOPER 實作",
        ]
    else:
        summary = f"識別為【{intent_label}】\n{analysis.summary}"
        suggested_actions = analysis.suggested_actions

    # 儲存 CEO 輸入到 DB
    status_val = "awaiting_confirmation" if analysis.requires_confirmation else "processing"
    created_at = datetime.utcnow()

    try:
        from app.db.database import AsyncSessionLocal
        from app.db.models import CeoInput
        async with AsyncSessionLocal() as session:
            db_input = CeoInput(
                id=input_id,
                content=request.content,
                source=request.source,
                input_type=request.input_type,
                intent=analysis.intent.value,
                confidence=analysis.confidence,
                summary=summary,
                status=status_val,
                route_to=analysis.route_to,
                analysis_result={
                    "entities": [{"type": e.entity_type, "value": e.value} for e in analysis.entities],
                    "suggested_actions": suggested_actions,
                    "meddic": analysis.meddic_analysis,
                    **extra_data,
                },
                created_at=created_at,
            )
            session.add(db_input)
            await session.commit()
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Failed to save CEO input: {e}")

    return CEOInputResponse(
        id=input_id,
        status=status_val,
        intent=analysis.intent.value,
        confidence=analysis.confidence,
        summary=summary,
        suggested_actions=suggested_actions,
        requires_confirmation=analysis.requires_confirmation,
        created_at=created_at.isoformat(),
    )


@router.get("/inputs")
async def list_ceo_inputs(
    status: Optional[str] = None,
    intent: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
):
    """取得 CEO 輸入列表"""
    from sqlalchemy import select, func
    from app.db.database import AsyncSessionLocal
    from app.db.models import CeoInput

    async with AsyncSessionLocal() as session:
        stmt = select(CeoInput)
        count_stmt = select(func.count()).select_from(CeoInput)

        if status:
            stmt = stmt.where(CeoInput.status == status)
            count_stmt = count_stmt.where(CeoInput.status == status)
        if intent:
            stmt = stmt.where(CeoInput.intent == intent)
            count_stmt = count_stmt.where(CeoInput.intent == intent)

        total_result = await session.execute(count_stmt)
        total = total_result.scalar() or 0

        stmt = stmt.order_by(CeoInput.created_at.desc()).offset(offset).limit(limit)
        result = await session.execute(stmt)
        rows = result.scalars().all()

        inputs = []
        for r in rows:
            inputs.append({
                "id": r.id,
                "content": r.content,
                "source": r.source,
                "input_type": r.input_type,
                "intent": r.intent,
                "confidence": r.confidence,
                "summary": r.summary,
                "status": r.status,
                "route_to": r.route_to,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            })

    return {
        "inputs": inputs,
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/inputs/pending")
async def list_pending_confirmations():
    """取得待確認的輸入"""
    from sqlalchemy import select, func
    from app.db.database import AsyncSessionLocal
    from app.db.models import CeoInput

    async with AsyncSessionLocal() as session:
        stmt = (
            select(CeoInput)
            .where(CeoInput.status == "awaiting_confirmation")
            .order_by(CeoInput.created_at.desc())
        )
        result = await session.execute(stmt)
        rows = result.scalars().all()

        inputs = []
        for r in rows:
            inputs.append({
                "id": r.id,
                "content": r.content,
                "intent": r.intent,
                "confidence": r.confidence,
                "summary": r.summary,
                "route_to": r.route_to,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            })

    return {
        "inputs": inputs,
        "count": len(inputs),
    }


@router.get("/inputs/{input_id}")
async def get_ceo_input(input_id: str):
    """取得特定輸入詳情"""
    from app.db.database import AsyncSessionLocal
    from app.db.models import CeoInput

    async with AsyncSessionLocal() as session:
        row = await session.get(CeoInput, input_id)
        if not row:
            raise HTTPException(status_code=404, detail="Input not found")

        return {
            "id": row.id,
            "content": row.content,
            "source": row.source,
            "input_type": row.input_type,
            "intent": row.intent,
            "confidence": row.confidence,
            "summary": row.summary,
            "status": row.status,
            "route_to": row.route_to,
            "analysis_result": row.analysis_result,
            "created_at": row.created_at.isoformat() if row.created_at else None,
            "confirmed_at": row.confirmed_at.isoformat() if row.confirmed_at else None,
        }


@router.get("/inputs/{input_id}/card")
async def get_confirmation_card(input_id: str):
    """取得確認卡片（用於 CEO Inbox）"""
    # TODO: 從 IntakeProcessor 取得
    return {
        "id": input_id,
        "type": "intake_confirmation",
        "actions": [
            {"id": "confirm", "label": "✓ 確認並執行"},
            {"id": "modify", "label": "✎ 修改"},
            {"id": "reject", "label": "✗ 取消"},
        ],
    }


@router.post("/inputs/{input_id}/confirm")
async def confirm_input(input_id: str, request: ConfirmationRequest):
    """
    CEO 確認輸入

    確認後：
    - 如果是商機：建立 Lead，通知 HUNTER
    - 如果是專案：建立需求，通知 ORCHESTRATOR
    """
    # TODO: 呼叫 IntakeProcessor.confirm

    if request.confirmed:
        return {
            "input_id": input_id,
            "status": "confirmed",
            "message": "輸入已確認，正在建立對應任務",
            "created_entity": {
                "type": "lead",
                "id": "LEAD-0001",
            },
            "routed_to": "HUNTER",
        }
    else:
        return {
            "input_id": input_id,
            "status": "rejected",
            "message": "輸入已取消",
            "feedback": request.feedback,
        }


@router.post("/inputs/{input_id}/modify")
async def modify_input(input_id: str, modifications: Dict[str, Any]):
    """修改輸入的解析結果"""
    # TODO: 呼叫 IntakeProcessor
    return {
        "input_id": input_id,
        "status": "modified",
        "modifications": modifications,
    }


@router.get("/summary")
async def get_intake_summary():
    """取得輸入統計摘要"""
    from sqlalchemy import select, func
    from app.db.database import AsyncSessionLocal
    from app.db.models import CeoInput

    async with AsyncSessionLocal() as session:
        total_r = await session.execute(select(func.count()).select_from(CeoInput))
        total = total_r.scalar() or 0

        pending_r = await session.execute(
            select(func.count()).select_from(CeoInput).where(CeoInput.status == "processing")
        )
        pending = pending_r.scalar() or 0

        awaiting_r = await session.execute(
            select(func.count()).select_from(CeoInput).where(CeoInput.status == "awaiting_confirmation")
        )
        awaiting = awaiting_r.scalar() or 0

        completed_r = await session.execute(
            select(func.count()).select_from(CeoInput).where(CeoInput.status == "confirmed")
        )
        completed = completed_r.scalar() or 0

        intent_r = await session.execute(
            select(CeoInput.intent, func.count()).group_by(CeoInput.intent)
        )
        by_intent = {row[0] or "unknown": row[1] for row in intent_r.all()}

    return IntakeSummary(
        total=total,
        pending=pending,
        awaiting_confirmation=awaiting,
        completed=completed,
        by_intent=by_intent,
    )


# === Quick Actions ===

@router.post("/quick/opportunity")
async def quick_create_opportunity(
    company: str,
    notes: str = "",
    contact_name: Optional[str] = None,
    contact_email: Optional[str] = None,
    urgency: str = "normal",
):
    """
    快速建立商機

    跳過解析流程，直接建立 Lead
    """
    from uuid import uuid4

    lead_id = f"LEAD-{uuid4().hex[:8].upper()}"

    # TODO: 直接建立 Lead

    return {
        "status": "created",
        "lead_id": lead_id,
        "company": company,
        "urgency": urgency,
        "message": f"已建立商機 {lead_id}，HUNTER 將開始跟進",
    }


@router.post("/quick/task")
async def quick_create_task(
    title: str,
    description: str = "",
    due_date: Optional[str] = None,
    assignee: Optional[str] = None,
):
    """快速建立待辦事項"""
    from uuid import uuid4

    task_id = f"TASK-{uuid4().hex[:8].upper()}"

    # TODO: 建立任務

    return {
        "status": "created",
        "task_id": task_id,
        "title": title,
        "message": f"已建立待辦事項 {task_id}",
    }


# === MEDDIC Analysis ===

class MEDDICRequest(BaseModel):
    """MEDDIC 分析請求"""
    content: str


@router.post("/analyze-meddic")
async def analyze_meddic(request: MEDDICRequest):
    """
    分析內容的 MEDDIC 指標

    返回 Pain, Champion, Economic Buyer 分析結果
    """
    from app.engines.meddic.engine import MEDDICEngine

    engine = MEDDICEngine()
    result = await engine.analyze(content=request.content)

    return result.to_dict()
