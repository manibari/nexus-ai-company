"""
PM Agent API Endpoints

產品經理 Agent 的 API 端點
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.agents.pm import PMAgent, FeatureRepository, FeatureStatus, get_pm_agent

router = APIRouter()


# === Request/Response Models ===

class FeatureRequestInput(BaseModel):
    """功能需求輸入"""
    content: str
    project: Optional[str] = None
    entities: List[Dict[str, Any]] = []
    intake_id: Optional[str] = None


class CEODecisionRequest(BaseModel):
    """CEO 決策請求"""
    action: str  # approve, modify, reject
    feedback: Optional[str] = None


class FeatureResponse(BaseModel):
    """功能需求回應"""
    id: str
    project_name: str
    title: str
    description: str
    status: str
    priority: str
    prd_summary: str
    user_story: str
    acceptance_criteria: List[str]
    technical_requirements: List[str]
    ui_requirements: List[str]
    estimated_effort: str
    estimated_days: int
    created_at: str
    approved_at: Optional[str] = None


# === API Endpoints ===

@router.post("/features")
async def create_feature_request(request: FeatureRequestInput):
    """
    建立功能需求

    從 CEO 輸入建立 Feature Request 和 PRD。
    """
    pm = get_pm_agent()

    result = await pm.process_feature_request(
        content=request.content,
        entities=request.entities,
        intake_id=request.intake_id,
    )

    return result


@router.get("/features")
async def list_features(
    project: Optional[str] = None,
    status: Optional[str] = None,
):
    """列出功能需求"""
    pm = get_pm_agent()
    features = await pm.list_features(project=project, status=status)
    return {"features": features, "total": len(features)}


@router.get("/features/{feature_id}")
async def get_feature(feature_id: str):
    """取得功能需求詳情"""
    pm = get_pm_agent()
    feature = await pm.get_feature(feature_id)

    if not feature:
        raise HTTPException(status_code=404, detail="Feature not found")

    return feature


@router.post("/features/{feature_id}/decision")
async def handle_ceo_decision(feature_id: str, request: CEODecisionRequest):
    """
    處理 CEO 決策

    CEO 可以：
    - approve: 批准開發，分派給 DEVELOPER
    - modify: 需要修改，退回 PM
    - reject: 取消功能需求
    """
    pm = get_pm_agent()

    result = await pm.handle_ceo_decision(
        feature_id=feature_id,
        action=request.action,
        feedback=request.feedback,
    )

    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    return result


@router.get("/stats")
async def get_pm_stats():
    """取得 PM 統計"""
    pm = get_pm_agent()
    all_features = await pm.list_features()

    stats = {
        "total": len(all_features),
        "by_status": {},
        "by_project": {},
        "by_priority": {},
    }

    for f in all_features:
        # By status
        status = f.get("status", "unknown")
        stats["by_status"][status] = stats["by_status"].get(status, 0) + 1

        # By project
        project = f.get("project_name", "unknown")
        stats["by_project"][project] = stats["by_project"].get(project, 0) + 1

        # By priority
        priority = f.get("priority", "unknown")
        stats["by_priority"][priority] = stats["by_priority"].get(priority, 0) + 1

    return stats


@router.get("/health")
async def pm_health():
    """PM Agent 健康檢查"""
    return {
        "status": "healthy",
        "agent": "PM",
        "name": "Product Manager",
    }
