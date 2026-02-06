"""
Agent Activity Log API

Agent 活動日誌 API 端點
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Query
from pydantic import BaseModel

from app.agents.activity_log import (
    ActivityLogRepository,
    ActivityType,
    get_activity_repo,
)

router = APIRouter()


class LogActivityRequest(BaseModel):
    """記錄活動請求"""
    agent_id: str
    agent_name: str
    activity_type: str  # task_start, task_end, status_change, blocked, unblocked, message, error, milestone
    message: str
    project_id: Optional[str] = None
    project_name: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


@router.get("/", response_model=List[Dict[str, Any]])
async def get_activity_log(
    limit: int = Query(50, ge=1, le=200),
    agent_id: Optional[str] = None,
    project_id: Optional[str] = None,
):
    """取得活動日誌"""
    repo = get_activity_repo()
    logs = await repo.get_recent(limit=limit, agent_id=agent_id, project_id=project_id)
    return [l.to_dict() for l in logs]


@router.get("/stats", response_model=Dict[str, Any])
async def get_activity_stats():
    """取得活動統計"""
    repo = get_activity_repo()
    return repo.get_stats()


@router.get("/agent/{agent_id}", response_model=List[Dict[str, Any]])
async def get_agent_timeline(agent_id: str, limit: int = Query(20, ge=1, le=100)):
    """取得特定 Agent 的活動時間線"""
    repo = get_activity_repo()
    logs = await repo.get_agent_timeline(agent_id, limit)
    return [l.to_dict() for l in logs]


@router.get("/agent/{agent_id}/today", response_model=Dict[str, Any])
async def get_agent_daily_summary(agent_id: str):
    """取得特定 Agent 的今日摘要（工時 + 任務列表）"""
    repo = get_activity_repo()
    return await repo.get_agent_daily_summary(agent_id)


@router.get("/daily-summary", response_model=List[Dict[str, Any]])
async def get_all_agents_daily_summary():
    """取得所有 Agent 的今日摘要"""
    repo = get_activity_repo()
    return await repo.get_all_agents_daily_summary()


@router.post("/", response_model=Dict[str, Any])
async def log_activity(request: LogActivityRequest):
    """記錄活動"""
    repo = get_activity_repo()

    try:
        activity_type = ActivityType(request.activity_type)
    except ValueError:
        activity_type = ActivityType.MESSAGE

    entry = await repo.log(
        agent_id=request.agent_id,
        agent_name=request.agent_name,
        activity_type=activity_type,
        message=request.message,
        project_id=request.project_id,
        project_name=request.project_name,
        metadata=request.metadata,
    )

    return entry.to_dict()
