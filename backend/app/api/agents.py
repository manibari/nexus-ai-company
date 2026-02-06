"""
Agent Management Endpoints
"""

from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()


class AgentStatus(BaseModel):
    """Agent 狀態模型"""
    id: str
    name: str
    role: str
    status: str  # idle, working, blocked_internal, blocked_user
    current_task: Optional[str] = None
    blocking_info: Optional[dict] = None


class AgentAction(BaseModel):
    """Agent 動作請求"""
    action: str
    params: Optional[dict] = None


# Mock data for MVP
MOCK_AGENTS = [
    AgentStatus(id="HUNTER", name="Sales Agent", role="業務", status="idle"),
    AgentStatus(id="ORCHESTRATOR", name="PM Agent", role="專案經理", status="idle"),
    AgentStatus(id="BUILDER", name="Engineer Agent", role="工程師", status="idle"),
    AgentStatus(id="INSPECTOR", name="QA Agent", role="測試員", status="idle"),
    AgentStatus(id="LEDGER", name="Finance Agent", role="財務", status="idle"),
    AgentStatus(id="GATEKEEPER", name="Admin Agent", role="行政", status="idle"),
]


@router.get("/", response_model=List[AgentStatus])
async def list_agents():
    """取得所有 Agent 狀態"""
    return MOCK_AGENTS


@router.get("/{agent_id}", response_model=AgentStatus)
async def get_agent(agent_id: str):
    """取得特定 Agent 狀態"""
    for agent in MOCK_AGENTS:
        if agent.id == agent_id:
            return agent
    raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")


class AgentStatusUpdate(BaseModel):
    """Agent 狀態更新請求"""
    status: str  # idle, working, blocked_internal, blocked_user
    current_task: Optional[str] = None
    blocking_info: Optional[dict] = None
    project_id: Optional[str] = None
    project_name: Optional[str] = None


@router.put("/{agent_id}/status", response_model=AgentStatus)
async def update_agent_status(agent_id: str, update: AgentStatusUpdate):
    """更新 Agent 狀態（供 Apple Intelligence / Local LLM 呼叫）"""
    from app.agents.activity_log import ActivityType, get_activity_repo

    for agent in MOCK_AGENTS:
        if agent.id == agent_id:
            old_status = agent.status
            old_current_task = agent.current_task  # 保存原任務名稱
            agent.status = update.status
            agent.current_task = update.current_task
            agent.blocking_info = update.blocking_info

            # 記錄活動日誌
            repo = get_activity_repo()

            # 判斷活動類型
            if update.status == "working" and old_status != "working":
                activity_type = ActivityType.TASK_START
                message = f"開始任務: {update.current_task or '未指定'}"
            elif update.status == "idle" and old_status == "working":
                activity_type = ActivityType.TASK_END
                message = f"完成任務: {old_current_task or '未指定'}"
            elif update.status in ("blocked_internal", "blocked_user"):
                activity_type = ActivityType.BLOCKED
                message = f"遭遇阻塞: {update.blocking_info or update.current_task or '未指定原因'}"
            elif old_status in ("blocked_internal", "blocked_user") and update.status not in ("blocked_internal", "blocked_user"):
                activity_type = ActivityType.UNBLOCKED
                message = f"解除阻塞"
            else:
                activity_type = ActivityType.STATUS_CHANGE
                message = f"狀態變更: {old_status} → {update.status}"

            await repo.log(
                agent_id=agent_id,
                agent_name=agent.name,
                activity_type=activity_type,
                message=message,
                project_id=update.project_id,
                project_name=update.project_name,
            )

            return agent
    raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")


@router.post("/{agent_id}/action")
async def trigger_agent_action(agent_id: str, action: AgentAction):
    """觸發 Agent 執行動作"""
    # TODO: Implement agent action triggering
    return {
        "agent_id": agent_id,
        "action": action.action,
        "status": "queued",
        "message": f"Action '{action.action}' queued for agent {agent_id}",
    }
