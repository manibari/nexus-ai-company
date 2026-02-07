"""
Agent Management Endpoints
"""

from typing import Dict, List, Optional

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


class AgentStatusUpdate(BaseModel):
    """Agent 狀態更新請求"""
    status: str  # idle, working, blocked_internal, blocked_user
    current_task: Optional[str] = None
    blocking_info: Optional[dict] = None
    project_id: Optional[str] = None
    project_name: Optional[str] = None


# 已知 Agent 角色定義（包含尚未註冊到 Registry 的 Agent）
AGENT_ROLES: Dict[str, str] = {
    "CEO": "執行長",
    "GATEKEEPER": "意圖分析",
    "PM": "產品經理",
    "HUNTER": "業務",
    "DEVELOPER": "工程師",
    "QA": "測試員",
    "ORCHESTRATOR": "專案協調",
}

# Runtime 狀態快取（記錄每個 Agent 目前的狀態）
_agent_states: Dict[str, AgentStatus] = {}


def _get_agent_status(agent_id: str) -> AgentStatus:
    """取得或建立 Agent 狀態物件"""
    if agent_id not in _agent_states:
        from app.agents.registry import get_registry
        registry = get_registry()
        reg_info = registry.get(agent_id)
        _agent_states[agent_id] = AgentStatus(
            id=agent_id,
            name=reg_info.agent_name if reg_info else agent_id,
            role=AGENT_ROLES.get(agent_id, "未知"),
            status="idle",
        )
    return _agent_states[agent_id]


@router.get("/", response_model=List[AgentStatus])
async def list_agents():
    """取得所有 Agent 狀態"""
    from app.agents.registry import get_registry
    registry = get_registry()
    registered = registry.list_agents()  # [{"id": "...", "name": "..."}]

    agents = []
    for agent_id, role in AGENT_ROLES.items():
        if agent_id in _agent_states:
            # 已有 runtime 狀態，更新 Registry 名稱
            agent = _agent_states[agent_id]
            reg_info = next((a for a in registered if a["id"] == agent_id), None)
            if reg_info:
                agent.name = reg_info["name"]
            agents.append(agent)
        else:
            # 首次查詢，從 Registry 取得名稱
            reg_info = next((a for a in registered if a["id"] == agent_id), None)
            agent = AgentStatus(
                id=agent_id,
                name=reg_info["name"] if reg_info else agent_id,
                role=role,
                status="idle",
            )
            _agent_states[agent_id] = agent
            agents.append(agent)
    return agents


@router.get("/{agent_id}", response_model=AgentStatus)
async def get_agent(agent_id: str):
    """取得特定 Agent 狀態"""
    if agent_id not in AGENT_ROLES:
        raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")
    return _get_agent_status(agent_id)


@router.put("/{agent_id}/status", response_model=AgentStatus)
async def update_agent_status(agent_id: str, update: AgentStatusUpdate):
    """更新 Agent 狀態（供 Apple Intelligence / Local LLM 呼叫）"""
    from app.agents.activity_log import ActivityType, get_activity_repo

    if agent_id not in AGENT_ROLES:
        raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")

    agent = _get_agent_status(agent_id)
    old_status = agent.status
    old_current_task = agent.current_task

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
