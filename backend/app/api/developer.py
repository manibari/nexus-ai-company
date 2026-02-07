"""
Developer Agent API Endpoints

開發者 Agent 的 API 端點
"""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException

from app.agents.developer import get_developer_agent

router = APIRouter()


@router.get("/health")
async def developer_health():
    """Developer Agent 健康檢查"""
    return {
        "status": "healthy",
        "agent": "DEVELOPER",
        "name": "Developer Agent",
    }


@router.get("/stats")
async def get_developer_stats():
    """取得開發統計"""
    agent = get_developer_agent()
    return agent.get_stats()


@router.get("/tasks")
async def list_developer_tasks(status: Optional[str] = None):
    """
    列出開發任務

    支援 status filter: developing, qa_dispatched, completed
    """
    agent = get_developer_agent()
    tasks = agent.get_tasks(status=status)
    return {"tasks": tasks, "total": len(tasks)}


@router.get("/tasks/{product_item_id}")
async def get_developer_task(product_item_id: str):
    """取得特定任務詳情 + 活動記錄"""
    agent = get_developer_agent()
    task = agent.get_task(product_item_id)

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # 取得相關活動記錄
    from app.agents.activity_log import get_activity_repo
    activity_repo = get_activity_repo()
    activities = await activity_repo.get_recent(limit=20, agent_id="DEVELOPER")

    # 過濾與此 product_item_id 相關的活動
    related_activities = [
        a.to_dict() for a in activities
        if a.metadata.get("product_item_id") == product_item_id
    ]

    return {
        "task": task,
        "activities": related_activities,
    }
