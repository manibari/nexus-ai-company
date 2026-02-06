"""
Goals API Endpoints

目標管理 API
時間單位：分鐘
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.goals.models import (
    Goal,
    GoalStatus,
    Phase,
    PhaseStatus,
    TimeEstimate,
    Priority,
    ChecklistItem,
)
from app.goals.repository import GoalRepository

router = APIRouter()

# 全域 Repository（Tracer Bullet 版本）
_repo = GoalRepository()


# === Request Models ===

class PhaseCreate(BaseModel):
    """建立階段"""
    name: str
    objective: str
    deliverables: List[str] = []
    acceptance_criteria: List[str] = []
    estimated_minutes: int = 30
    buffer_minutes: int = 5
    assignee: Optional[str] = None


class GoalCreate(BaseModel):
    """建立目標"""
    title: str
    objective: str
    success_criteria: List[str] = []
    in_scope: List[str] = []
    out_of_scope: List[str] = []
    estimated_minutes: int = 120
    buffer_minutes: int = 30
    priority: str = "medium"
    phases: List[PhaseCreate] = []
    owner: str = "ORCHESTRATOR"
    assignees: List[str] = []
    notes: Optional[str] = None


class GoalUpdate(BaseModel):
    """更新目標"""
    title: Optional[str] = None
    objective: Optional[str] = None
    priority: Optional[str] = None
    notes: Optional[str] = None


class PhaseUpdate(BaseModel):
    """更新階段"""
    name: Optional[str] = None
    objective: Optional[str] = None
    notes: Optional[str] = None
    blockers: Optional[List[str]] = None


class CheckpointAction(BaseModel):
    """確認點動作"""
    action: str  # approve, reject
    comments: Optional[str] = None
    reviewed_by: str = "CEO"


class CheckItemAction(BaseModel):
    """勾選項目"""
    completed_by: str


# === Goal Endpoints ===

@router.post("", response_model=Dict[str, Any])
async def create_goal(request: GoalCreate):
    """
    建立目標

    自動建立 Phases 和 Checkpoints
    """
    # 建立 phases
    phases = []
    for i, phase_data in enumerate(request.phases):
        phase = Phase(
            id="",  # 會在 __post_init__ 自動生成
            goal_id="",  # 稍後設定
            name=phase_data.name,
            objective=phase_data.objective,
            sequence=i,
            deliverables=phase_data.deliverables,
            acceptance_criteria=phase_data.acceptance_criteria,
            time_estimate=TimeEstimate(
                estimated_minutes=phase_data.estimated_minutes,
                buffer_minutes=phase_data.buffer_minutes,
            ),
            assignee=phase_data.assignee,
        )
        phases.append(phase)

    # 建立 goal
    goal = Goal(
        id="",  # 會在 __post_init__ 自動生成
        title=request.title,
        objective=request.objective,
        success_criteria=request.success_criteria,
        in_scope=request.in_scope,
        out_of_scope=request.out_of_scope,
        time_estimate=TimeEstimate(
            estimated_minutes=request.estimated_minutes,
            buffer_minutes=request.buffer_minutes,
        ),
        priority=Priority(request.priority),
        owner=request.owner,
        assignees=request.assignees,
        notes=request.notes,
    )

    # 設定 phase 的 goal_id
    for phase in phases:
        phase.goal_id = goal.id
    goal.phases = phases

    # 儲存
    await _repo.create(goal)

    return goal.to_dict()


@router.get("", response_model=List[Dict[str, Any]])
async def list_goals(
    status: Optional[str] = None,
    priority: Optional[str] = None,
    owner: Optional[str] = None,
    limit: int = 50,
):
    """列出目標"""
    goals = await _repo.list(
        status=GoalStatus(status) if status else None,
        priority=Priority(priority) if priority else None,
        owner=owner,
        limit=limit,
    )
    return [g.to_summary() for g in goals]


@router.get("/active", response_model=List[Dict[str, Any]])
async def list_active_goals():
    """列出活躍的目標"""
    goals = await _repo.list_active()
    return [g.to_dict() for g in goals]


@router.get("/statistics", response_model=Dict[str, Any])
async def get_statistics():
    """取得統計資訊"""
    return _repo.get_statistics()


@router.get("/{goal_id}", response_model=Dict[str, Any])
async def get_goal(goal_id: str):
    """取得目標詳情"""
    goal = await _repo.get(goal_id)
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    return goal.to_dict()


@router.put("/{goal_id}", response_model=Dict[str, Any])
async def update_goal(goal_id: str, request: GoalUpdate):
    """更新目標"""
    goal = await _repo.get(goal_id)
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")

    if request.title:
        goal.title = request.title
    if request.objective:
        goal.objective = request.objective
    if request.priority:
        goal.priority = Priority(request.priority)
    if request.notes:
        goal.notes = request.notes

    await _repo.update(goal)
    return goal.to_dict()


@router.post("/{goal_id}/start", response_model=Dict[str, Any])
async def start_goal(goal_id: str):
    """開始目標"""
    goal = await _repo.get(goal_id)
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")

    goal.start()

    # 自動開始第一個 phase
    if goal.next_phase:
        goal.next_phase.start()

    await _repo.update(goal)
    return goal.to_dict()


@router.post("/{goal_id}/complete", response_model=Dict[str, Any])
async def complete_goal(goal_id: str):
    """完成目標"""
    goal = await _repo.get(goal_id)
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")

    # 檢查所有 phases 是否完成
    incomplete = [p for p in goal.phases if p.status != PhaseStatus.COMPLETED]
    if incomplete:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot complete goal: {len(incomplete)} phases not completed"
        )

    goal.complete()
    await _repo.update(goal)
    return goal.to_dict()


@router.delete("/{goal_id}")
async def cancel_goal(goal_id: str):
    """取消目標"""
    goal = await _repo.get(goal_id)
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")

    goal.status = GoalStatus.CANCELLED
    await _repo.update(goal)
    return {"message": f"Goal {goal_id} cancelled"}


# === Phase Endpoints ===

@router.get("/{goal_id}/phases", response_model=List[Dict[str, Any]])
async def list_phases(goal_id: str):
    """列出目標的所有階段"""
    goal = await _repo.get(goal_id)
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    return [p.to_dict() for p in goal.phases]


@router.post("/{goal_id}/phases", response_model=Dict[str, Any])
async def add_phase(goal_id: str, request: PhaseCreate):
    """新增階段"""
    goal = await _repo.get(goal_id)
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")

    phase = Phase(
        id="",
        goal_id=goal_id,
        name=request.name,
        objective=request.objective,
        sequence=len(goal.phases),
        deliverables=request.deliverables,
        acceptance_criteria=request.acceptance_criteria,
        time_estimate=TimeEstimate(
            estimated_minutes=request.estimated_minutes,
            buffer_minutes=request.buffer_minutes,
        ),
        assignee=request.assignee,
    )

    goal.phases.append(phase)
    await _repo.update(goal)
    return phase.to_dict()


@router.post("/phases/{phase_id}/start", response_model=Dict[str, Any])
async def start_phase(phase_id: str):
    """開始階段"""
    phase = await _repo.start_phase(phase_id)
    if not phase:
        raise HTTPException(status_code=404, detail="Phase not found")
    return phase.to_dict()


@router.post("/phases/{phase_id}/complete", response_model=Dict[str, Any])
async def complete_phase(phase_id: str):
    """完成階段"""
    phase = await _repo.get_phase(phase_id)
    if not phase:
        raise HTTPException(status_code=404, detail="Phase not found")

    # 檢查 checkpoint
    if phase.checkpoint and not phase.checkpoint.all_checked:
        raise HTTPException(
            status_code=400,
            detail="Cannot complete phase: not all checklist items are completed"
        )

    phase = await _repo.complete_phase(phase_id)

    # 自動開始下一個 phase
    goal = await _repo.get(phase.goal_id)
    if goal and goal.next_phase:
        goal.next_phase.start()
        await _repo.update(goal)

    return phase.to_dict()


@router.put("/phases/{phase_id}", response_model=Dict[str, Any])
async def update_phase(phase_id: str, request: PhaseUpdate):
    """更新階段"""
    phase = await _repo.get_phase(phase_id)
    if not phase:
        raise HTTPException(status_code=404, detail="Phase not found")

    if request.name:
        phase.name = request.name
    if request.objective:
        phase.objective = request.objective
    if request.notes:
        phase.notes = request.notes
    if request.blockers is not None:
        phase.blockers = request.blockers

    await _repo.update_phase(phase)
    return phase.to_dict()


# === Checkpoint Endpoints ===

@router.post("/phases/{phase_id}/checkpoint", response_model=Dict[str, Any])
async def checkpoint_action(phase_id: str, request: CheckpointAction):
    """確認點動作（核准/退回）"""
    if request.action == "approve":
        checkpoint = await _repo.approve_checkpoint(
            phase_id, request.reviewed_by, request.comments
        )
    elif request.action == "reject":
        if not request.comments:
            raise HTTPException(status_code=400, detail="Comments required for rejection")
        checkpoint = await _repo.reject_checkpoint(
            phase_id, request.reviewed_by, request.comments
        )
    else:
        raise HTTPException(status_code=400, detail="Invalid action")

    if not checkpoint:
        raise HTTPException(status_code=404, detail="Checkpoint not found")
    return checkpoint.to_dict()


@router.post("/phases/{phase_id}/checklist/{item_id}", response_model=Dict[str, Any])
async def check_item(phase_id: str, item_id: str, request: CheckItemAction):
    """勾選檢查項目"""
    success = await _repo.check_item(phase_id, item_id, request.completed_by)
    if not success:
        raise HTTPException(status_code=404, detail="Item not found")

    phase = await _repo.get_phase(phase_id)
    return phase.checkpoint.to_dict()


# === Dashboard Endpoints ===

@router.get("/dashboard/overview", response_model=Dict[str, Any])
async def dashboard_overview():
    """Dashboard 概覽"""
    goals = await _repo.list(limit=100)
    active_goals = [g for g in goals if g.status == GoalStatus.ACTIVE]
    overdue = [g for g in goals if g.is_overdue]
    at_risk = [g for g in goals if g.health == "at_risk"]

    return {
        "total_goals": len(goals),
        "active_goals": len(active_goals),
        "overdue_goals": len(overdue),
        "at_risk_goals": len(at_risk),
        "goals": [g.to_summary() for g in active_goals],
        "alerts": [
            {"type": "overdue", "goal_id": g.id, "title": g.title}
            for g in overdue
        ] + [
            {"type": "at_risk", "goal_id": g.id, "title": g.title}
            for g in at_risk
        ],
    }
