"""
Agents Module

AI Agent 決策層
"""

# 延遲導入以避免循環依賴
# from app.agents.base import Agent, AgentConfig, AgentStatus, ThinkResult
from app.agents.gatekeeper import GatekeeperAgent, Intent, IntakeAnalysis, analyze_input
from app.agents.hunter import HunterAgent, HunterAction, process_opportunity, get_suggestion
from app.agents.orchestrator import OrchestratorAgent, OrchestratorAction, process_project, get_goal_status

__all__ = [
    # Base
    "Agent",
    "AgentConfig",
    "AgentStatus",
    "ThinkResult",
    # Gatekeeper
    "GatekeeperAgent",
    "Intent",
    "IntakeAnalysis",
    "analyze_input",
    # Hunter
    "HunterAgent",
    "HunterAction",
    "process_opportunity",
    "get_suggestion",
    # Orchestrator
    "OrchestratorAgent",
    "OrchestratorAction",
    "process_project",
    "get_goal_status",
]
