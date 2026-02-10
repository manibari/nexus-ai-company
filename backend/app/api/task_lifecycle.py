"""
Task Lifecycle API Endpoints

Router prefix: /api/v1/task（singular，獨立於既有 /api/v1/tasks）

8 個 REST endpoints 管理 Task 全生命週期。

Issue #14
"""

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()
logger = logging.getLogger(__name__)


# === Request / Response Models ===

class CreateTaskRequest(BaseModel):
    intent: str
    title: Optional[str] = None
    description: Optional[str] = None
    priority: int = 2
    source: str = "manual"


class TransitionRequest(BaseModel):
    trigger: str
    actor: str
    payload: Optional[Dict[str, Any]] = None


class SavePlanRequest(BaseModel):
    plan_json: Dict[str, Any]
    routing_risk: float = 0.0
    risk_factors: Optional[List[str]] = None


class UATRequest(BaseModel):
    action: str  # "confirm" | "request_fix"
    comment: Optional[str] = None


# === Endpoints ===

@router.post("/")
async def create_task(request: CreateTaskRequest):
    """建立 Task（status=submitted，寫 TASK_SUBMITTED event）"""
    from app.task.repository import get_task_repo

    repo = get_task_repo()

    task = await repo.create_task(
        intent=request.intent,
        priority=request.priority,
        source=request.source,
        title=request.title,
        description=request.description,
    )

    # 記錄 TASK_SUBMITTED event
    await repo.record_event(
        task_id=task["id"],
        event_type="TASK_SUBMITTED",
        actor="user:ceo",
        from_status=None,
        to_status="submitted",
        payload={"intent": request.intent, "source": request.source},
        trace_id=task["trace_id"],
    )

    # WS broadcast
    await _broadcast_task_update(task)

    return task


@router.get("/")
async def list_tasks(status: Optional[str] = None, limit: int = 50):
    """列表（?status=&limit=50）"""
    from app.task.repository import get_task_repo

    repo = get_task_repo()
    tasks = await repo.list_tasks(status=status, limit=limit)
    return {"tasks": tasks, "count": len(tasks)}


@router.get("/{task_id}")
async def get_task(task_id: str):
    """取得 Task 詳情 + 最新 plan"""
    from app.task.repository import get_task_repo

    repo = get_task_repo()
    task = await repo.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    plan = await repo.get_execution_plan(task_id)
    task["execution_plan"] = plan

    return task


@router.get("/{task_id}/events")
async def get_task_events(task_id: str):
    """取得 Event 歷史"""
    from app.task.repository import get_task_repo

    repo = get_task_repo()

    # 確認 task 存在
    task = await repo.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    events = await repo.get_task_events(task_id)
    return {"task_id": task_id, "events": events, "count": len(events)}


@router.post("/{task_id}/transition")
async def transition_task(task_id: str, request: TransitionRequest):
    """
    觸發狀態轉換。

    1. 從 DB 讀取 task.lifecycle_status
    2. 建構 TaskLifecycle(initial_state=current_status)
    3. try_trigger(trigger) → 驗證轉換合法性
    4. 成功：更新 DB status + record_event + WS broadcast
    5. 失敗：return 400
    """
    from app.task.repository import get_task_repo
    from app.core.task_state_machine import TaskLifecycle

    repo = get_task_repo()

    task = await repo.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    current_status = task["lifecycle_status"]
    if not current_status:
        raise HTTPException(status_code=400, detail="Task has no lifecycle_status")

    # 建構狀態機並嘗試轉換
    machine = TaskLifecycle(initial_state=current_status)
    ok, result = machine.try_trigger(request.trigger)

    if not ok:
        raise HTTPException(status_code=400, detail=result)

    new_status = result

    # 更新 retry_count（schema_fail_retry 時遞增）
    retry_count = task.get("retry_count", 0)
    if request.trigger == "schema_fail_retry":
        retry_count += 1

    # 更新 DB
    updated = await repo.update_lifecycle_status(
        task_id=task_id,
        new_status=new_status,
        retry_count=retry_count if request.trigger == "schema_fail_retry" else None,
    )

    # 記錄 event
    event = await repo.record_event(
        task_id=task_id,
        event_type=f"TRANSITION_{request.trigger.upper()}",
        actor=request.actor,
        from_status=current_status,
        to_status=new_status,
        payload=request.payload,
        trace_id=task.get("trace_id"),
    )

    # WS broadcast
    await _broadcast_task_update(updated)

    return {
        "task_id": task_id,
        "from_status": current_status,
        "to_status": new_status,
        "trigger": request.trigger,
        "event_id": event["id"],
    }


@router.post("/{task_id}/plan")
async def save_plan(task_id: str, request: SavePlanRequest):
    """儲存 Execution Plan"""
    from app.task.repository import get_task_repo

    repo = get_task_repo()

    task = await repo.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    plan = await repo.save_execution_plan(
        task_id=task_id,
        plan_json=request.plan_json,
        routing_risk=request.routing_risk,
        risk_factors=request.risk_factors,
    )

    # 記錄 event
    await repo.record_event(
        task_id=task_id,
        event_type="PLAN_GENERATED",
        actor="system:routing_governance",
        from_status=task["lifecycle_status"],
        to_status=task["lifecycle_status"],
        payload={"plan_id": plan["id"], "routing_risk": request.routing_risk},
        trace_id=task.get("trace_id"),
    )

    return plan


@router.post("/{task_id}/plan/approve")
async def approve_plan(task_id: str):
    """CEO 核准 Plan"""
    from app.task.repository import get_task_repo
    from app.core.task_state_machine import TaskLifecycle

    repo = get_task_repo()

    task = await repo.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    # 核准 plan
    approved = await repo.approve_plan(task_id)
    if not approved:
        raise HTTPException(status_code=404, detail="No execution plan found")

    # 如果目前在 plan_review，自動轉換到 plan_approved
    current_status = task["lifecycle_status"]
    if current_status == "plan_review":
        machine = TaskLifecycle(initial_state=current_status)
        ok, new_status = machine.try_trigger("approve_plan")
        if ok:
            await repo.update_lifecycle_status(task_id, new_status)
            await repo.record_event(
                task_id=task_id,
                event_type="PLAN_APPROVED",
                actor="user:ceo",
                from_status=current_status,
                to_status=new_status,
                payload={"plan_id": approved["id"]},
                trace_id=task.get("trace_id"),
            )

    return {
        "task_id": task_id,
        "plan": approved,
        "message": "Plan approved",
    }


@router.post("/{task_id}/uat")
async def uat_decision(task_id: str, request: UATRequest):
    """CEO UAT 驗收"""
    from app.task.repository import get_task_repo
    from app.core.task_state_machine import TaskLifecycle

    repo = get_task_repo()

    task = await repo.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    current_status = task["lifecycle_status"]
    if current_status != "uat_review":
        raise HTTPException(
            status_code=400,
            detail=f"Task is in '{current_status}', expected 'uat_review'",
        )

    if request.action == "confirm":
        trigger = "confirm_uat"
    elif request.action == "request_fix":
        trigger = "request_fix"
    else:
        raise HTTPException(status_code=400, detail=f"Invalid action: {request.action}")

    machine = TaskLifecycle(initial_state=current_status)
    ok, result = machine.try_trigger(trigger)

    if not ok:
        raise HTTPException(status_code=400, detail=result)

    new_status = result

    await repo.update_lifecycle_status(task_id, new_status)

    event = await repo.record_event(
        task_id=task_id,
        event_type=f"UAT_{request.action.upper()}",
        actor="user:ceo",
        from_status=current_status,
        to_status=new_status,
        payload={"comment": request.comment} if request.comment else {},
        trace_id=task.get("trace_id"),
    )

    updated = await repo.get_task(task_id)
    await _broadcast_task_update(updated)

    return {
        "task_id": task_id,
        "action": request.action,
        "from_status": current_status,
        "to_status": new_status,
        "event_id": event["id"],
    }


# === Helpers ===

async def _broadcast_task_update(task: dict):
    """透過 WebSocket 廣播 task 狀態更新"""
    try:
        from app.agents.ws_manager import get_ws_manager
        mgr = get_ws_manager()
        if mgr:
            await mgr.broadcast({
                "type": "task_lifecycle",
                "task_id": task.get("id"),
                "lifecycle_status": task.get("lifecycle_status"),
                "trace_id": task.get("trace_id"),
            })
    except Exception as e:
        logger.warning(f"WS broadcast failed: {e}")
