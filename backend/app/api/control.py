"""
Agent Control Endpoints

CEO 控制 Agent 的 API：
- 執行模式設定
- 檢查點審批
- 動作回滾
- 規則管理
"""

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.core.execution_mode import ExecutionMode, CheckpointStatus
from app.core.action_journal import ActionStatus
from app.core.pipeline_gate import OverrideAction

router = APIRouter()


# === 執行模式 ===

class ExecutionModeUpdate(BaseModel):
    """執行模式更新"""
    agent_id: str
    mode: str  # "auto", "supervised", "review"
    dry_run: bool = False


@router.post("/agents/{agent_id}/execution-mode")
async def set_agent_execution_mode(agent_id: str, update: ExecutionModeUpdate):
    """設定 Agent 執行模式"""
    # TODO: 實作實際的模式更新
    return {
        "agent_id": agent_id,
        "mode": update.mode,
        "dry_run": update.dry_run,
        "message": f"Execution mode set to '{update.mode}' for agent {agent_id}",
    }


# === 檢查點管理 ===

class CheckpointApproval(BaseModel):
    """檢查點審批"""
    approved: bool
    feedback: Optional[str] = None


@router.get("/checkpoints")
async def list_pending_checkpoints(agent_id: Optional[str] = None):
    """取得待審批的檢查點"""
    # TODO: 從 ExecutionController 取得
    return {
        "checkpoints": [],
        "count": 0,
    }


@router.post("/checkpoints/{checkpoint_id}/approve")
async def approve_checkpoint(checkpoint_id: str, approval: CheckpointApproval):
    """審批檢查點"""
    # TODO: 呼叫 ExecutionController.approve_checkpoint 或 reject_checkpoint
    action = "approved" if approval.approved else "rejected"
    return {
        "checkpoint_id": checkpoint_id,
        "action": action,
        "feedback": approval.feedback,
    }


# === 動作日誌 ===

@router.get("/actions")
async def list_actions(
    agent_id: Optional[str] = None,
    task_id: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 50,
):
    """取得動作列表"""
    # TODO: 從 ActionJournal 取得
    return {
        "actions": [],
        "count": 0,
    }


@router.get("/actions/reversible")
async def list_reversible_actions(agent_id: Optional[str] = None):
    """取得可撤回的動作"""
    # TODO: 從 ActionJournal 取得
    return {
        "actions": [],
        "count": 0,
    }


class RevertRequest(BaseModel):
    """撤回請求"""
    reason: str = ""


@router.post("/actions/{action_id}/revert")
async def revert_action(action_id: str, request: RevertRequest):
    """撤回動作"""
    # TODO: 呼叫 ActionJournal.revert
    return {
        "action_id": action_id,
        "status": "reverted",
        "reason": request.reason,
    }


class MistakeReport(BaseModel):
    """錯誤標記"""
    feedback: str


@router.post("/actions/{action_id}/mistake")
async def mark_as_mistake(action_id: str, report: MistakeReport):
    """標記動作為錯誤"""
    # TODO: 呼叫 ActionJournal.mark_as_mistake
    return {
        "action_id": action_id,
        "status": "marked_mistake",
        "feedback": report.feedback,
    }


# === Pipeline 覆寫 ===

class PipelineOverrideRequest(BaseModel):
    """Pipeline 覆寫請求"""
    action: str  # "pause", "resume", "force_stage", "skip", "abort"
    target_stage: Optional[str] = None
    reason: str = ""


@router.post("/pipeline/{entity_type}/{entity_id}/override")
async def override_pipeline(
    entity_type: str,
    entity_id: str,
    request: PipelineOverrideRequest,
):
    """執行 Pipeline 覆寫"""
    # TODO: 呼叫 PipelineGateManager.override
    return {
        "entity_type": entity_type,
        "entity_id": entity_id,
        "action": request.action,
        "target_stage": request.target_stage,
        "reason": request.reason,
        "status": "executed",
    }


@router.post("/pipeline/{entity_type}/{entity_id}/pause")
async def pause_entity(entity_type: str, entity_id: str, reason: str = ""):
    """暫停實體處理"""
    return {
        "entity_id": entity_id,
        "status": "paused",
        "reason": reason,
    }


@router.post("/pipeline/{entity_type}/{entity_id}/resume")
async def resume_entity(entity_type: str, entity_id: str):
    """恢復實體處理"""
    return {
        "entity_id": entity_id,
        "status": "resumed",
    }


# === 規則管理 ===

@router.get("/rules")
async def list_all_rules():
    """取得所有 Agent 規則"""
    # TODO: 從 RulesEngine 取得
    return {
        "rules": {},
    }


@router.get("/rules/{agent_id}")
async def get_agent_rules(agent_id: str):
    """取得特定 Agent 規則"""
    # TODO: 從 RulesEngine 取得
    return {
        "agent_id": agent_id,
        "rules": {},
    }


class RuleUpdate(BaseModel):
    """規則更新"""
    path: str  # e.g., "approval_thresholds.discount_percentage"
    value: any


@router.patch("/rules/{agent_id}")
async def update_agent_rules(agent_id: str, updates: List[RuleUpdate]):
    """更新 Agent 規則"""
    # TODO: 呼叫 RulesEngine.update_rules
    return {
        "agent_id": agent_id,
        "updated_fields": [u.path for u in updates],
        "message": f"Rules updated for agent {agent_id}",
    }


# === 指標 ===

@router.get("/metrics")
async def get_all_metrics(period: str = "daily"):
    """取得所有 Agent 指標"""
    # TODO: 從 MetricsCollector 取得
    return {
        "period": period,
        "agents": {},
        "summary": {},
    }


@router.get("/metrics/{agent_id}")
async def get_agent_metrics(agent_id: str, period: str = "daily"):
    """取得特定 Agent 指標"""
    # TODO: 從 MetricsCollector 取得
    return {
        "agent_id": agent_id,
        "period": period,
        "metrics": {},
    }


@router.get("/metrics/report")
async def export_metrics_report(period: str = "daily", format: str = "json"):
    """匯出指標報告"""
    # TODO: 從 MetricsCollector.export_report 取得
    return {
        "report_type": "agent_performance",
        "period": period,
        "format": format,
        "data": {},
    }


# === 錯誤學習 ===

@router.get("/learning/mistakes")
async def list_mistakes(agent_id: Optional[str] = None):
    """取得錯誤記錄（用於學習）"""
    # TODO: 從 ActionJournal 取得
    return {
        "mistakes": [],
        "count": 0,
    }


@router.get("/learning/suggestions/{agent_id}")
async def get_improvement_suggestions(agent_id: str):
    """取得改進建議"""
    # TODO: 基於錯誤記錄生成建議
    return {
        "agent_id": agent_id,
        "suggestions": [],
    }
