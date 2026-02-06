"""
Dashboard & KPI Endpoints
"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class KPIResponse(BaseModel):
    """KPI 回應"""
    # Financial
    burn_rate_daily_usd: float
    total_cost_usd: float
    revenue_usd: float

    # Pipeline
    sales_pipeline_value: float
    leads_count: dict  # by stage
    tasks_count: dict  # by stage

    # Agents
    agents_status: dict  # by status

    # Time
    timestamp: datetime


@router.get("/kpi", response_model=KPIResponse)
async def get_kpi():
    """取得即時 KPI"""
    # TODO: Calculate from actual data
    return KPIResponse(
        burn_rate_daily_usd=0.0,
        total_cost_usd=0.0,
        revenue_usd=0.0,
        sales_pipeline_value=0.0,
        leads_count={
            "new_lead": 0,
            "qualified": 0,
            "contacted": 0,
            "engaged": 0,
            "closed_won": 0,
            "closed_lost": 0,
        },
        tasks_count={
            "backlog": 0,
            "spec_ready": 0,
            "in_progress": 0,
            "qa_testing": 0,
            "uat": 0,
            "done": 0,
        },
        agents_status={
            "idle": 6,
            "working": 0,
            "blocked_internal": 0,
            "blocked_user": 0,
        },
        timestamp=datetime.utcnow(),
    )


@router.get("/timeline")
async def get_timeline(
    hours: int = 24,
    agent_id: Optional[str] = None,
):
    """取得活動時間軸"""
    # TODO: Query from logs table
    return {
        "events": [],
        "period_hours": hours,
        "agent_filter": agent_id,
    }


@router.get("/ledger")
async def get_ledger(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
):
    """取得財務帳本"""
    # TODO: Query from ledger table
    return {
        "entries": [],
        "summary": {
            "total_input_tokens": 0,
            "total_output_tokens": 0,
            "total_cost_usd": 0.0,
            "by_provider": {},
            "by_agent": {},
        },
    }
