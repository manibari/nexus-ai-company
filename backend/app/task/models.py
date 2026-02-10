"""
Task Lifecycle Domain Models

ID 產生器 + TaskStatus 列舉。

Issue #14
"""

from datetime import datetime
from enum import Enum
from uuid import uuid4


class TaskStatus(str, Enum):
    SUBMITTED = "submitted"
    PLANNING = "planning"
    PLAN_REVIEW = "plan_review"
    PLAN_APPROVED = "plan_approved"
    REASONING = "reasoning"
    DRAFT_GENERATED = "draft_generated"
    SCHEMA_CHECK = "schema_check"
    RULE_CHECK = "rule_check"
    DRAFT_REVIEW = "draft_review"
    DRAFT_APPROVED = "draft_approved"
    EXECUTING = "executing"
    UAT_REVIEW = "uat_review"
    COMPLETED = "completed"
    REJECTED = "rejected"
    ESCALATED = "escalated"


TERMINAL_STATES = {TaskStatus.COMPLETED, TaskStatus.REJECTED, TaskStatus.ESCALATED}


def generate_task_id() -> str:
    """產生 Task ID: TSK-YYYYMMDD-XXXX"""
    date_str = datetime.utcnow().strftime("%Y%m%d")
    short = uuid4().hex[:4].upper()
    return f"TSK-{date_str}-{short}"


def generate_event_id() -> str:
    """產生 Event ID: EVT-YYYYMMDD-XXXX"""
    date_str = datetime.utcnow().strftime("%Y%m%d")
    short = uuid4().hex[:4].upper()
    return f"EVT-{date_str}-{short}"


def generate_plan_id() -> str:
    """產生 Execution Plan ID: EP-YYYYMMDD-XXXX"""
    date_str = datetime.utcnow().strftime("%Y%m%d")
    short = uuid4().hex[:4].upper()
    return f"EP-{date_str}-{short}"


def generate_trace_id() -> str:
    """產生 Trace ID: trc-{uuid hex}"""
    return f"trc-{uuid4().hex}"
