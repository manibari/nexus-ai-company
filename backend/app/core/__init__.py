"""
Core Module - Agent 可觀測性與可控制性

包含：
- ExecutionMode: 執行模式控制
- ActionJournal: 動作日誌與回滾
- PipelineGate: Pipeline 關卡機制
- RulesEngine: 行為規則引擎
- AgentMetrics: 績效追蹤
"""

from app.core.execution_mode import (
    ExecutionMode,
    ExecutionContext,
    StepCheckpoint,
    CheckpointStatus,
)
from app.core.action_journal import (
    ActionRecord,
    ActionJournal,
    ActionStatus,
)
from app.core.pipeline_gate import (
    PipelineGate,
    GateType,
    PipelineOverride,
    OverrideAction,
)
from app.core.rules_engine import (
    AgentRules,
    RulesEngine,
)
from app.core.metrics import (
    AgentMetrics,
    MetricsCollector,
)

__all__ = [
    # Execution Mode
    "ExecutionMode",
    "ExecutionContext",
    "StepCheckpoint",
    "CheckpointStatus",
    # Action Journal
    "ActionRecord",
    "ActionJournal",
    "ActionStatus",
    # Pipeline Gate
    "PipelineGate",
    "GateType",
    "PipelineOverride",
    "OverrideAction",
    # Rules Engine
    "AgentRules",
    "RulesEngine",
    # Metrics
    "AgentMetrics",
    "MetricsCollector",
]
