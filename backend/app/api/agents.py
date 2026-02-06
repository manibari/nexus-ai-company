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
