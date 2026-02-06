"""
Knowledge Repository

知識庫儲存與查詢（Tracer Bullet: 使用記憶體儲存）
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4

from app.knowledge.models import (
    KnowledgeCard,
    KnowledgeStatus,
    KnowledgeType,
    SearchResult,
)

logger = logging.getLogger(__name__)


class KnowledgeRepository:
    """
    知識庫 Repository

    Tracer Bullet 版本：使用記憶體儲存
    Production 版本：改用 PostgreSQL
    """

    def __init__(self):
        self._store: Dict[str, KnowledgeCard] = {}
        self._id_counter = 0

    def _generate_id(self) -> str:
        """生成知識 ID"""
        self._id_counter += 1
        year = datetime.now().year
        return f"KB-{year}-{self._id_counter:04d}"

    async def create(
        self,
        type: KnowledgeType,
        title: str,
        content: str,
        summary: Optional[str] = None,
        category: Optional[str] = None,
        tags: List[str] = None,
        metadata: Dict[str, Any] = None,
        created_by: Optional[str] = None,
    ) -> KnowledgeCard:
        """建立知識卡片"""
        card = KnowledgeCard(
            id=self._generate_id(),
            type=type,
            title=title,
            content=content,
            summary=summary,
            category=category,
            tags=tags or [],
            metadata=metadata or {},
            created_by=created_by,
        )

        self._store[card.id] = card
        logger.info(f"Created knowledge card: {card.id} - {card.title}")

        return card

    async def get(self, id: str) -> Optional[KnowledgeCard]:
        """取得知識卡片"""
        card = self._store.get(id)
        if card:
            card.usage_count += 1
        return card

    async def update(
        self,
        id: str,
        **kwargs
    ) -> Optional[KnowledgeCard]:
        """更新知識卡片"""
        card = self._store.get(id)
        if not card:
            return None

        for key, value in kwargs.items():
            if hasattr(card, key):
                setattr(card, key, value)

        card.updated_at = datetime.utcnow()
        return card

    async def delete(self, id: str) -> bool:
        """刪除知識卡片（軟刪除）"""
        card = self._store.get(id)
        if not card:
            return False

        card.status = KnowledgeStatus.ARCHIVED
        return True

    async def search(
        self,
        query: Optional[str] = None,
        filters: Dict[str, Any] = None,
        limit: int = 20,
    ) -> List[SearchResult]:
        """
        搜尋知識

        Args:
            query: 搜尋關鍵字
            filters: 過濾條件 (type, category, tags, metadata)
            limit: 回傳數量限制
        """
        results = []
        filters = filters or {}

        for card in self._store.values():
            # 只搜尋已發布的
            if card.status != KnowledgeStatus.PUBLISHED:
                continue

            # 過濾條件
            if not card.matches_filters(filters):
                continue

            # 關鍵字匹配
            if query:
                if not card.matches_query(query):
                    continue
                # 簡單評分：匹配的關鍵字數量
                score = sum(1 for term in query.lower().split()
                           if term in card.title.lower()) * 2
                score += sum(1 for term in query.lower().split()
                            if term in card.content.lower())
            else:
                score = 1.0

            results.append(SearchResult(card=card, score=score))

        # 排序
        results.sort(key=lambda x: x.score, reverse=True)

        return results[:limit]

    async def list_by_type(
        self,
        type: KnowledgeType,
        limit: int = 20
    ) -> List[KnowledgeCard]:
        """依類型列表"""
        return [
            card for card in self._store.values()
            if card.type == type and card.status == KnowledgeStatus.PUBLISHED
        ][:limit]

    async def get_tags(self) -> Dict[str, int]:
        """取得所有標籤及數量"""
        tag_counts = {}
        for card in self._store.values():
            if card.status != KnowledgeStatus.PUBLISHED:
                continue
            for tag in card.tags:
                tag_counts[tag] = tag_counts.get(tag, 0) + 1
        return dict(sorted(tag_counts.items(), key=lambda x: x[1], reverse=True))

    async def get_categories(self) -> Dict[str, int]:
        """取得所有分類及數量"""
        cat_counts = {}
        for card in self._store.values():
            if card.status != KnowledgeStatus.PUBLISHED:
                continue
            if card.category:
                cat_counts[card.category] = cat_counts.get(card.category, 0) + 1
        return cat_counts

    def count(self) -> int:
        """取得知識數量"""
        return len([c for c in self._store.values()
                   if c.status == KnowledgeStatus.PUBLISHED])
