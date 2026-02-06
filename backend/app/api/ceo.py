"""
CEO Decision Endpoints
"""

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()


class InboxItem(BaseModel):
    """CEO Inbox 項目"""
    id: str
    from_agent: str
    subject: str
    payload: dict
    priority: int  # 1-4
    status: str  # pending, approved, rejected
    created_at: datetime


class ApprovalRequest(BaseModel):
    """審批請求"""
    decision: str  # "approve" or "reject"
    feedback: Optional[str] = None


# Mock inbox data
MOCK_INBOX: List[InboxItem] = []


@router.get("/inbox", response_model=List[InboxItem])
async def get_inbox(status: Optional[str] = "pending"):
    """取得 CEO Inbox 待辦事項"""
    if status:
        return [item for item in MOCK_INBOX if item.status == status]
    return MOCK_INBOX


@router.get("/inbox/{item_id}", response_model=InboxItem)
async def get_inbox_item(item_id: str):
    """取得特定 Inbox 項目"""
    for item in MOCK_INBOX:
        if item.id == item_id:
            return item
    raise HTTPException(status_code=404, detail=f"Inbox item {item_id} not found")


@router.post("/inbox/{item_id}/decide")
async def make_decision(item_id: str, request: ApprovalRequest):
    """
    CEO 做出決策

    這會：
    1. 更新 Inbox 項目狀態
    2. 解除相關 Agent 的阻擋狀態
    3. 觸發後續流程
    """
    for item in MOCK_INBOX:
        if item.id == item_id:
            item.status = "approved" if request.decision == "approve" else "rejected"

            # TODO: Notify the requesting agent
            # TODO: Unblock the agent
            # TODO: Trigger next pipeline stage

            return {
                "item_id": item_id,
                "decision": request.decision,
                "feedback": request.feedback,
                "message": f"Decision '{request.decision}' recorded for item {item_id}",
            }

    raise HTTPException(status_code=404, detail=f"Inbox item {item_id} not found")


@router.get("/stats")
async def get_ceo_stats():
    """取得 CEO 儀表板統計"""
    pending_count = len([i for i in MOCK_INBOX if i.status == "pending"])

    return {
        "inbox_pending": pending_count,
        "agents_active": 0,  # TODO: Calculate from actual agent status
        "agents_blocked": 0,
        "tasks_in_progress": 0,
        "tasks_awaiting_uat": 0,
    }
