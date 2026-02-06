"""
Sales Pipeline Module

銷售管道管理
"""

from app.pipeline.models import (
    Opportunity,
    OpportunityStage,
    OpportunityStatus,
    Contact,
    ContactRole,
    Activity,
    ActivityType,
)
from app.pipeline.repository import PipelineRepository

__all__ = [
    "Opportunity",
    "OpportunityStage",
    "OpportunityStatus",
    "Contact",
    "ContactRole",
    "Activity",
    "ActivityType",
    "PipelineRepository",
]
