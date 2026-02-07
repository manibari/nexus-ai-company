"""
CEO To-Do API Endpoints

CEO 待辦系統 API
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.ceo.models import (
    TodoItem,
    TodoAction,
    TodoType,
    TodoPriority,
    TodoStatus,
)
from app.ceo.repository import TodoRepository

router = APIRouter()

# 全域 Repository（SQLAlchemy 版本）
_repo = None


def _get_repo() -> TodoRepository:
    global _repo
    if _repo is None:
        from app.db.database import AsyncSessionLocal
        _repo = TodoRepository(session_factory=AsyncSessionLocal)
    return _repo


# === Request Models ===

class TodoCreate(BaseModel):
    """建立待辦"""
    project_name: str
    subject: str
    description: Optional[str] = None
    from_agent: str = "SYSTEM"
    from_agent_name: str = "System"
    type: str = "notification"
    priority: str = "normal"
    deadline_hours: Optional[int] = None  # 幾小時後到期
    actions: List[Dict[str, Any]] = []
    related_entity_type: Optional[str] = None
    related_entity_id: Optional[str] = None
    payload: Dict[str, Any] = {}


class TodoRespond(BaseModel):
    """回覆待辦"""
    action_id: str
    data: Optional[Dict[str, Any]] = None


class TodoSnooze(BaseModel):
    """延後處理"""
    hours: int = 24


# === Endpoints ===

@router.get("/todos", response_model=List[Dict[str, Any]])
async def list_todos(
    status: Optional[str] = None,
    priority: Optional[str] = None,
    limit: int = 50,
):
    """取得待辦清單"""
    status_enum = None
    priority_enum = None

    if status:
        try:
            status_enum = TodoStatus(status)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status}")

    if priority:
        try:
            priority_enum = TodoPriority(priority)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid priority: {priority}")

    todos = await _get_repo().list(status=status_enum, priority=priority_enum, limit=limit)
    return [t.to_dict() for t in todos]


@router.get("/todos/pending", response_model=List[Dict[str, Any]])
async def list_pending_todos():
    """取得待處理的待辦"""
    todos = await _get_repo().list_pending()
    return [t.to_dict() for t in todos]


@router.get("/todos/stats", response_model=Dict[str, Any])
async def get_todo_stats():
    """取得待辦統計"""
    return await _get_repo().get_stats_async()


@router.get("/todos/{todo_id}", response_model=Dict[str, Any])
async def get_todo(todo_id: str):
    """取得待辦詳情"""
    todo = await _get_repo().get(todo_id)
    if not todo:
        raise HTTPException(status_code=404, detail="Todo not found")
    return todo.to_dict()


@router.post("/todos", response_model=Dict[str, Any])
async def create_todo(request: TodoCreate):
    """建立待辦（Agent 呼叫）"""
    # 解析類型
    try:
        todo_type = TodoType(request.type)
    except ValueError:
        todo_type = TodoType.NOTIFICATION

    try:
        todo_priority = TodoPriority(request.priority)
    except ValueError:
        todo_priority = TodoPriority.NORMAL

    # 計算 deadline
    deadline = None
    if request.deadline_hours:
        deadline = datetime.utcnow() + timedelta(hours=request.deadline_hours)

    # 建立 actions
    actions = []
    for a in request.actions:
        actions.append(TodoAction(
            id=a.get("id", "action"),
            label=a.get("label", "確認"),
            style=a.get("style", "default"),
            requires_input=a.get("requires_input", False),
            input_placeholder=a.get("input_placeholder"),
        ))

    # 如果沒有指定 actions，根據類型給預設
    if not actions:
        if todo_type == TodoType.APPROVAL:
            actions = [
                TodoAction(id="approve", label="同意", style="primary"),
                TodoAction(id="reject", label="拒絕", style="danger"),
            ]
        elif todo_type == TodoType.REVIEW:
            actions = [
                TodoAction(id="pass", label="通過", style="primary"),
                TodoAction(id="reject", label="退回", style="danger", requires_input=True, input_placeholder="退回原因"),
            ]
        elif todo_type == TodoType.QUESTIONNAIRE:
            actions = [
                TodoAction(id="respond", label="填寫問卷", style="primary"),
                TodoAction(id="skip", label="稍後處理", style="default"),
            ]
        elif todo_type == TodoType.DECISION:
            actions = [
                TodoAction(id="decide", label="選擇方案", style="primary"),
            ]
        else:
            actions = [
                TodoAction(id="acknowledge", label="確認已讀", style="default"),
            ]

    todo = TodoItem(
        id="",
        project_name=request.project_name,
        subject=request.subject,
        description=request.description,
        from_agent=request.from_agent,
        from_agent_name=request.from_agent_name,
        type=todo_type,
        priority=todo_priority,
        deadline=deadline,
        actions=actions,
        related_entity_type=request.related_entity_type,
        related_entity_id=request.related_entity_id,
        payload=request.payload,
    )

    await _get_repo().create(todo)
    return todo.to_dict()


@router.post("/todos/{todo_id}/respond", response_model=Dict[str, Any])
async def respond_todo(todo_id: str, request: TodoRespond):
    """CEO 回覆待辦"""
    # 先取得 todo 資訊（含 callback）
    todo = await _get_repo().get(todo_id)
    if not todo:
        raise HTTPException(status_code=404, detail="Todo not found")

    # 標記為已完成
    todo = await _get_repo().respond(todo_id, request.action_id, request.data)

    # 觸發 callback（如果有）
    callback_result = None
    if todo.payload and todo.payload.get("callback_endpoint"):
        callback_result = await _trigger_callback(
            todo=todo,
            action_id=request.action_id,
            response_data=request.data,
        )

    result = todo.to_dict()
    if callback_result:
        result["callback_result"] = callback_result

    return result


async def _trigger_callback(
    todo: TodoItem,
    action_id: str,
    response_data: Optional[Dict[str, Any]] = None,
) -> Optional[Dict[str, Any]]:
    """觸發 Todo callback（通知原始 Agent）"""
    import logging
    logger = logging.getLogger(__name__)

    callback_endpoint = todo.payload.get("callback_endpoint", "")

    # PM Feature Decision callback
    if "/pm/features/" in callback_endpoint and "/decision" in callback_endpoint:
        try:
            from app.agents.pm import get_pm_agent
            feature_id = todo.payload.get("feature_id")
            if not feature_id:
                logger.error("Missing feature_id in callback payload")
                return {"error": "Missing feature_id"}

            pm = get_pm_agent()

            # 轉換 action_id 為 PM 決策
            feedback = None
            if response_data and response_data.get("input"):
                feedback = response_data.get("input")

            result = await pm.handle_ceo_decision(
                feature_id=feature_id,
                action=action_id,
                feedback=feedback,
            )

            logger.info(f"PM callback triggered for {feature_id}: {action_id}")
            return result

        except Exception as e:
            logger.error(f"PM callback failed: {e}")
            return {"error": str(e)}

    # 其他 Agent callback 可在此擴展
    return None


@router.post("/todos/{todo_id}/snooze", response_model=Dict[str, Any])
async def snooze_todo(todo_id: str, request: TodoSnooze):
    """延後處理"""
    todo = await _get_repo().snooze(todo_id, request.hours)
    if not todo:
        raise HTTPException(status_code=404, detail="Todo not found")
    return todo.to_dict()


@router.delete("/todos/{todo_id}")
async def delete_todo(todo_id: str):
    """刪除待辦"""
    success = await _get_repo().delete(todo_id)
    if not success:
        raise HTTPException(status_code=404, detail="Todo not found")
    return {"message": f"Todo {todo_id} deleted"}
