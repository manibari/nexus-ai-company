"""
QA Agent API Endpoints

品質保證 Agent 的 API 端點
"""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException

from app.agents.qa import get_qa_agent

router = APIRouter()


@router.get("/health")
async def qa_health():
    """QA Agent 健康檢查"""
    return {
        "status": "healthy",
        "agent": "QA",
        "name": "QA Agent",
    }


@router.get("/stats")
async def get_qa_stats():
    """
    取得 QA 統計

    回傳 testing, passed, failed, bugs_reported, pass_rate
    """
    agent = get_qa_agent()
    return agent.get_stats()


@router.get("/results")
async def list_qa_results(status: Optional[str] = None):
    """
    列出 QA 結果

    支援 status filter: passed, failed, reported
    """
    agent = get_qa_agent()
    results = agent.get_results(status=status)
    return {"results": results, "total": len(results)}


@router.get("/results/{product_item_id}")
async def get_qa_result(product_item_id: str):
    """取得特定項目 QA 詳情 + 活動記錄"""
    agent = get_qa_agent()
    result = agent.get_result(product_item_id)

    if not result:
        raise HTTPException(status_code=404, detail="QA result not found")

    # 取得相關活動記錄
    from app.agents.activity_log import get_activity_repo
    activity_repo = get_activity_repo()
    activities = await activity_repo.get_recent(limit=20, agent_id="QA")

    # 過濾與此 product_item_id 相關的活動
    related_activities = [
        a.to_dict() for a in activities
        if a.metadata.get("product_item_id") == product_item_id
    ]

    return {
        "result": result,
        "activities": related_activities,
    }


@router.post("/results/{product_item_id}/retest")
async def retest_product_item(product_item_id: str):
    """
    排程重新測試

    重新對指定 ProductItem 執行 QA 測試流程
    """
    from app.product.repository import get_product_repo

    product_repo = get_product_repo()
    product_item = await product_repo.get(product_item_id)

    if not product_item:
        raise HTTPException(status_code=404, detail="ProductItem not found")

    # 透過 registry dispatch 重新測試
    from app.agents.registry import get_registry
    registry = get_registry()

    dispatch_result = await registry.dispatch(
        target_id="QA",
        payload={
            "content": product_item.description,
            "product_item_id": product_item_id,
            "feature_id": product_item.source_input_id,
            "project": product_item.tags[0] if product_item.tags else "Unknown",
            "title": product_item.title,
            "requirements": {
                "acceptance_criteria": product_item.acceptance_criteria,
            },
            "implementation_plan": {},
        },
        from_agent="QA_API",
    )

    return {
        "status": "retest_scheduled",
        "product_item_id": product_item_id,
        "dispatch_result": dispatch_result,
    }
