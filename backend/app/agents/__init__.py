"""
Agents Module

AI Agent 決策層

Agent 分類：
1. 輕量級 Agent (使用 Gemini 2.5 Flash)
   - GATEKEEPER: 意圖分析
   - HUNTER: 商機追蹤
   - PM: 產品管理
   - ORCHESTRATOR: 任務協調

2. 開發 Agent (使用 Claude Code CLI)
   - DEVELOPER: 程式碼撰寫
   - QA: 測試撰寫
"""

# 延遲導入以避免循環依賴
from app.agents.gatekeeper import GatekeeperAgent, Intent, IntakeAnalysis, analyze_input
from app.agents.hunter import HunterAgent, HunterAction, process_opportunity, get_suggestion
from app.agents.orchestrator import OrchestratorAgent, OrchestratorAction, process_project, get_goal_status
from app.agents.pm import PMAgent, PMAction, FeatureRequest, process_feature, handle_decision
from app.agents.registry import AgentRegistry, AgentHandler, get_registry, set_registry

__all__ = [
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
    # PM
    "PMAgent",
    "PMAction",
    "FeatureRequest",
    "process_feature",
    "handle_decision",
    # Registry
    "AgentRegistry",
    "AgentHandler",
    "get_registry",
    "set_registry",
]
