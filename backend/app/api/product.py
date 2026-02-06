"""
Product API Router

產品開發管理 API
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.product.models import (
    ProductItem,
    ProductStage,
    ProductPriority,
    ProductType,
)
from app.product.repository import ProductRepository


router = APIRouter()
_repo = ProductRepository()


# === Request Models ===

class ProductCreate(BaseModel):
    title: str
    description: str
    type: str = "feature"
    priority: str = "medium"
    version: Optional[str] = None
    target_release: Optional[str] = None
    spec_doc: Optional[str] = None
    acceptance_criteria: Optional[List[str]] = None
    estimated_hours: Optional[float] = None
    tags: Optional[List[str]] = None


class ProductUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    type: Optional[str] = None
    priority: Optional[str] = None
    version: Optional[str] = None
    target_release: Optional[str] = None
    spec_doc: Optional[str] = None
    acceptance_criteria: Optional[List[str]] = None
    estimated_hours: Optional[float] = None
    actual_hours: Optional[float] = None
    notes: Optional[str] = None
    tags: Optional[List[str]] = None


class AssignRequest(BaseModel):
    assignee: str


class QAResultRequest(BaseModel):
    test_name: str
    passed: bool
    details: Optional[str] = None


class UATFeedbackRequest(BaseModel):
    feedback: str
    approved: Optional[bool] = None


class BlockRequest(BaseModel):
    reason: str
    blocked_by: Optional[str] = None


class UnblockRequest(BaseModel):
    return_to_stage: str


# === Endpoints ===

@router.post("", response_model=Dict[str, Any])
async def create_product(request: ProductCreate):
    """建立產品項目"""
    product = ProductItem(
        id="",
        title=request.title,
        description=request.description,
        type=ProductType(request.type),
        priority=ProductPriority(request.priority),
        version=request.version,
        target_release=request.target_release,
        spec_doc=request.spec_doc,
        acceptance_criteria=request.acceptance_criteria or [],
        estimated_hours=request.estimated_hours,
        tags=request.tags or [],
    )
    await _repo.create(product)
    return product.to_dict()


@router.get("", response_model=List[Dict[str, Any]])
async def list_products(
    stage: Optional[str] = None,
    type: Optional[str] = None,
    priority: Optional[str] = None,
    assignee: Optional[str] = None,
    version: Optional[str] = None,
    limit: int = 100,
):
    """列出產品項目"""
    products = await _repo.list(
        stage=ProductStage(stage) if stage else None,
        product_type=ProductType(type) if type else None,
        priority=ProductPriority(priority) if priority else None,
        assignee=assignee,
        version=version,
        limit=limit,
    )
    return [p.to_dict() for p in products]


@router.get("/dashboard", response_model=Dict[str, Any])
async def get_dashboard():
    """取得儀表板摘要"""
    return _repo.get_dashboard()


@router.get("/roadmap", response_model=Dict[str, List[Dict[str, Any]]])
async def get_roadmap():
    """取得版本 Roadmap"""
    return _repo.get_roadmap()


@router.get("/statistics", response_model=Dict[str, Any])
async def get_statistics():
    """取得統計資訊"""
    return _repo.get_statistics()


@router.get("/{product_id}", response_model=Dict[str, Any])
async def get_product(product_id: str):
    """取得產品詳情"""
    product = await _repo.get(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product.to_dict()


@router.put("/{product_id}", response_model=Dict[str, Any])
async def update_product(product_id: str, request: ProductUpdate):
    """更新產品"""
    product = await _repo.get(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    if request.title is not None:
        product.title = request.title
    if request.description is not None:
        product.description = request.description
    if request.type is not None:
        product.type = ProductType(request.type)
    if request.priority is not None:
        product.priority = ProductPriority(request.priority)
    if request.version is not None:
        product.version = request.version
    if request.target_release is not None:
        product.target_release = request.target_release
    if request.spec_doc is not None:
        product.spec_doc = request.spec_doc
    if request.acceptance_criteria is not None:
        product.acceptance_criteria = request.acceptance_criteria
    if request.estimated_hours is not None:
        product.estimated_hours = request.estimated_hours
    if request.actual_hours is not None:
        product.actual_hours = request.actual_hours
    if request.notes is not None:
        product.notes = request.notes
    if request.tags is not None:
        product.tags = request.tags

    await _repo.update(product)
    return product.to_dict()


@router.delete("/{product_id}")
async def delete_product(product_id: str):
    """刪除產品"""
    success = await _repo.delete(product_id)
    if not success:
        raise HTTPException(status_code=404, detail="Product not found")
    return {"status": "deleted", "id": product_id}


@router.post("/{product_id}/advance", response_model=Dict[str, Any])
async def advance_stage(product_id: str):
    """推進到下一階段"""
    product = await _repo.get(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # Check if can advance
    from app.product.models import STAGE_ORDER
    try:
        current_idx = STAGE_ORDER.index(product.stage)
        if current_idx < len(STAGE_ORDER) - 1:
            next_stage = STAGE_ORDER[current_idx + 1]
            can_advance, blockers = product.can_advance_to(next_stage)
            if not can_advance:
                raise HTTPException(
                    status_code=400,
                    detail={"message": "Cannot advance", "blockers": blockers}
                )
    except ValueError:
        raise HTTPException(status_code=400, detail="Cannot advance from blocked state")

    result = await _repo.advance_stage(product_id)
    if not result:
        raise HTTPException(status_code=400, detail="Failed to advance stage")
    return result.to_dict()


@router.post("/{product_id}/stage/{stage}", response_model=Dict[str, Any])
async def set_stage(product_id: str, stage: str):
    """設定特定階段"""
    try:
        target_stage = ProductStage(stage)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid stage: {stage}")

    result = await _repo.set_stage(product_id, target_stage)
    if not result:
        raise HTTPException(status_code=400, detail="Cannot set to this stage")
    return result.to_dict()


@router.post("/{product_id}/assign", response_model=Dict[str, Any])
async def assign_product(product_id: str, request: AssignRequest):
    """指派 Agent"""
    result = await _repo.assign(product_id, request.assignee)
    if not result:
        raise HTTPException(status_code=404, detail="Product not found")
    return result.to_dict()


@router.post("/{product_id}/qa", response_model=Dict[str, Any])
async def add_qa_result(product_id: str, request: QAResultRequest):
    """新增 QA 測試結果"""
    result = await _repo.add_qa_result(
        product_id,
        test_name=request.test_name,
        passed=request.passed,
        details=request.details,
    )
    if not result:
        raise HTTPException(status_code=404, detail="Product not found")
    return result.to_dict()


@router.post("/{product_id}/uat", response_model=Dict[str, Any])
async def add_uat_feedback(product_id: str, request: UATFeedbackRequest):
    """新增 UAT 回饋"""
    result = await _repo.add_uat_feedback(
        product_id,
        feedback=request.feedback,
        approved=request.approved,
    )
    if not result:
        raise HTTPException(status_code=404, detail="Product not found")
    return result.to_dict()


@router.post("/{product_id}/block", response_model=Dict[str, Any])
async def block_product(product_id: str, request: BlockRequest):
    """標記為阻擋"""
    result = await _repo.block(
        product_id,
        reason=request.reason,
        blocked_by=request.blocked_by,
    )
    if not result:
        raise HTTPException(status_code=404, detail="Product not found")
    return result.to_dict()


@router.post("/{product_id}/unblock", response_model=Dict[str, Any])
async def unblock_product(product_id: str, request: UnblockRequest):
    """解除阻擋"""
    try:
        return_stage = ProductStage(request.return_to_stage)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid stage: {request.return_to_stage}")

    result = await _repo.unblock(product_id, return_stage)
    if not result:
        raise HTTPException(status_code=400, detail="Product not found or not blocked")
    return result.to_dict()
