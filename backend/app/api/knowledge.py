"""
Knowledge Base API Router

公司知識庫 API
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.knowledge.models import (
    KnowledgeCard,
    KnowledgeType,
    KnowledgeStatus,
)
from app.knowledge.repository import KnowledgeRepository


router = APIRouter()
_repo = KnowledgeRepository()


# === Request Models ===

class KnowledgeCreate(BaseModel):
    title: str
    content: str
    type: str = "document"
    summary: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None


class KnowledgeUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    type: Optional[str] = None
    summary: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None
    status: Optional[str] = None


class SearchQuery(BaseModel):
    query: str
    type: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[List[str]] = None
    limit: int = 20


# === Endpoints ===

@router.post("", response_model=Dict[str, Any])
async def create_knowledge(request: KnowledgeCreate):
    """建立知識卡"""
    card = KnowledgeCard(
        id="",
        title=request.title,
        content=request.content,
        type=KnowledgeType(request.type),
        summary=request.summary,
        category=request.category,
        tags=request.tags or [],
        metadata=request.metadata or {},
    )
    await _repo.create(card)
    return card.to_dict()


@router.get("", response_model=List[Dict[str, Any]])
async def list_knowledge(
    type: Optional[str] = None,
    category: Optional[str] = None,
    tag: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 50,
):
    """列出知識卡"""
    filters = {}
    if type:
        filters["type"] = type
    if category:
        filters["category"] = category
    if tag:
        filters["tags"] = [tag]
    if status:
        filters["status"] = status

    if filters:
        results = await _repo.search(query="", filters=filters, limit=limit)
    else:
        # List all published cards
        results = await _repo.search(query="", filters={"status": "published"}, limit=limit)

    return [r.to_dict() for r in results]


@router.get("/search", response_model=List[Dict[str, Any]])
async def search_knowledge(
    q: str,
    type: Optional[str] = None,
    category: Optional[str] = None,
    limit: int = 20,
):
    """搜尋知識"""
    filters = {}
    if type:
        filters["type"] = type
    if category:
        filters["category"] = category

    results = await _repo.search(query=q, filters=filters, limit=limit)
    return [r.to_dict() for r in results]


@router.get("/tags", response_model=Dict[str, int])
async def get_tags():
    """取得所有標籤及數量"""
    return await _repo.get_tags()


@router.get("/categories", response_model=Dict[str, int])
async def get_categories():
    """取得所有分類及數量"""
    return await _repo.get_categories()


@router.get("/types", response_model=List[Dict[str, str]])
async def get_types():
    """取得知識類型"""
    return [
        {"value": t.value, "label": t.value.replace("_", " ").title()}
        for t in KnowledgeType
    ]


@router.get("/statistics", response_model=Dict[str, Any])
async def get_statistics():
    """取得使用統計"""
    all_cards = await _repo.search(query="", filters={}, limit=1000)

    # Count by type
    type_counts = {}
    for card in all_cards:
        t = card.type.value
        type_counts[t] = type_counts.get(t, 0) + 1

    # Count by status
    status_counts = {}
    for card in all_cards:
        s = card.status.value
        status_counts[s] = status_counts.get(s, 0) + 1

    # Top used cards
    top_used = sorted(all_cards, key=lambda c: c.usage_count, reverse=True)[:5]

    # Recently added
    recent = sorted(all_cards, key=lambda c: c.created_at, reverse=True)[:5]

    return {
        "total": len(all_cards),
        "published": await _repo.count(),
        "by_type": type_counts,
        "by_status": status_counts,
        "top_used": [{"id": c.id, "title": c.title, "usage_count": c.usage_count} for c in top_used],
        "recent": [{"id": c.id, "title": c.title, "created_at": c.created_at.isoformat()} for c in recent],
    }


@router.get("/{card_id}", response_model=Dict[str, Any])
async def get_knowledge(card_id: str):
    """取得知識詳情（會增加使用次數）"""
    card = await _repo.get(card_id)
    if not card:
        raise HTTPException(status_code=404, detail="Knowledge card not found")
    return card.to_dict()


@router.put("/{card_id}", response_model=Dict[str, Any])
async def update_knowledge(card_id: str, request: KnowledgeUpdate):
    """更新知識"""
    card = await _repo.get(card_id)
    if not card:
        raise HTTPException(status_code=404, detail="Knowledge card not found")

    updates = {}
    if request.title is not None:
        updates["title"] = request.title
    if request.content is not None:
        updates["content"] = request.content
    if request.type is not None:
        updates["type"] = KnowledgeType(request.type)
    if request.summary is not None:
        updates["summary"] = request.summary
    if request.category is not None:
        updates["category"] = request.category
    if request.tags is not None:
        updates["tags"] = request.tags
    if request.metadata is not None:
        updates["metadata"] = request.metadata
    if request.status is not None:
        updates["status"] = KnowledgeStatus(request.status)

    updated = await _repo.update(card_id, **updates)
    if not updated:
        raise HTTPException(status_code=500, detail="Failed to update")
    return updated.to_dict()


@router.delete("/{card_id}")
async def delete_knowledge(card_id: str):
    """刪除知識（軟刪除，標記為 archived）"""
    success = await _repo.delete(card_id)
    if not success:
        raise HTTPException(status_code=404, detail="Knowledge card not found")
    return {"status": "archived", "id": card_id}
