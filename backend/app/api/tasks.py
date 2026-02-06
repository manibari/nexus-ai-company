"""
Task Management Endpoints
"""

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()


class TaskCreate(BaseModel):
    """建立任務請求"""
    title: str
    description: Optional[str] = None
    pipeline: str  # "sales" or "product"
    assigned_to: Optional[str] = None


class TaskResponse(BaseModel):
    """任務回應"""
    id: str
    title: str
    description: Optional[str]
    pipeline: str
    stage: str
    assigned_to: Optional[str]
    created_at: datetime
    updated_at: datetime


# Mock data
MOCK_TASKS: List[TaskResponse] = []


@router.get("/", response_model=List[TaskResponse])
async def list_tasks(
    pipeline: Optional[str] = None,
    stage: Optional[str] = None,
    assigned_to: Optional[str] = None,
):
    """取得任務列表（支援篩選）"""
    tasks = MOCK_TASKS

    if pipeline:
        tasks = [t for t in tasks if t.pipeline == pipeline]
    if stage:
        tasks = [t for t in tasks if t.stage == stage]
    if assigned_to:
        tasks = [t for t in tasks if t.assigned_to == assigned_to]

    return tasks


@router.post("/", response_model=TaskResponse)
async def create_task(task: TaskCreate):
    """建立新任務"""
    now = datetime.utcnow()
    new_task = TaskResponse(
        id=f"TASK-{len(MOCK_TASKS) + 1:04d}",
        title=task.title,
        description=task.description,
        pipeline=task.pipeline,
        stage="new_lead" if task.pipeline == "sales" else "backlog",
        assigned_to=task.assigned_to,
        created_at=now,
        updated_at=now,
    )
    MOCK_TASKS.append(new_task)
    return new_task


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(task_id: str):
    """取得特定任務"""
    for task in MOCK_TASKS:
        if task.id == task_id:
            return task
    raise HTTPException(status_code=404, detail=f"Task {task_id} not found")


@router.patch("/{task_id}/stage")
async def update_task_stage(task_id: str, stage: str):
    """更新任務階段"""
    for task in MOCK_TASKS:
        if task.id == task_id:
            task.stage = stage
            task.updated_at = datetime.utcnow()
            return {"message": f"Task {task_id} moved to stage '{stage}'"}

    raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
