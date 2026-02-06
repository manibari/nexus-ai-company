"""
CEO Intake API Endpoints

接收和處理 CEO 的非結構化輸入
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

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

    自動進行：
    1. 意圖識別
    2. 實體解析
    3. 資訊補全（如果是商機）
    4. 結構化

    如果需要確認，會推送到 CEO Inbox
    """
    # TODO: 呼叫 IntakeProcessor
    from uuid import uuid4

    input_id = str(uuid4())

    # 模擬處理結果
    return CEOInputResponse(
        id=input_id,
        status="awaiting_confirmation",
        intent="opportunity",
        confidence=0.85,
        summary="識別為【商機線索】\n公司：待解析\n緊急程度：normal",
        suggested_actions=[
            "建立 Lead 並進入 Sales Pipeline",
            "由 HUNTER 開始跟進",
        ],
        requires_confirmation=True,
        created_at=datetime.utcnow().isoformat(),
    )


@router.get("/inputs")
async def list_ceo_inputs(
    status: Optional[str] = None,
    intent: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
):
    """取得 CEO 輸入列表"""
    # TODO: 從 IntakeProcessor 取得
    return {
        "inputs": [],
        "total": 0,
        "limit": limit,
        "offset": offset,
    }


@router.get("/inputs/pending")
async def list_pending_confirmations():
    """取得待確認的輸入"""
    # TODO: 從 IntakeProcessor 取得
    return {
        "inputs": [],
        "count": 0,
    }


@router.get("/inputs/{input_id}")
async def get_ceo_input(input_id: str):
    """取得特定輸入詳情"""
    # TODO: 從 IntakeProcessor 取得
    return {
        "id": input_id,
        "status": "not_found",
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
    # TODO: 從 IntakeProcessor 取得
    return IntakeSummary(
        total=0,
        pending=0,
        awaiting_confirmation=0,
        completed=0,
        by_intent={
            "opportunity": 0,
            "project": 0,
            "question": 0,
            "task": 0,
            "info": 0,
        },
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
