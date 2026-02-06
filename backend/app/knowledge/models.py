"""
Knowledge Management Models

知識管理資料模型
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class KnowledgeType(Enum):
    """知識類型"""
    CASE = "case"
    PROJECT = "project"
    DOCUMENT = "document"
    TEMPLATE = "template"
    PROCEDURE = "procedure"
    INSIGHT = "insight"
    LESSON = "lesson"


class KnowledgeStatus(Enum):
    """知識狀態"""
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"
    DEPRECATED = "deprecated"


@dataclass
class KnowledgeCard:
    """知識卡片"""
    id: str
    type: KnowledgeType
    title: str
    content: str
    summary: Optional[str] = None

    # 分類
    category: Optional[str] = None
    tags: List[str] = field(default_factory=list)

    # 結構化資料
    metadata: Dict[str, Any] = field(default_factory=dict)

    # 關聯
    related_ids: List[str] = field(default_factory=list)

    # 狀態
    status: KnowledgeStatus = KnowledgeStatus.PUBLISHED

    # 生命週期
    created_by: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    # 統計
    usage_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type.value,
            "title": self.title,
            "summary": self.summary,
            "content": self.content,
            "category": self.category,
            "tags": self.tags,
            "metadata": self.metadata,
            "status": self.status.value,
            "usage_count": self.usage_count,
        }

    def matches_query(self, query: str) -> bool:
        """簡單的關鍵字匹配"""
        query_lower = query.lower()
        searchable = f"{self.title} {self.content} {' '.join(self.tags)}".lower()
        return all(term in searchable for term in query_lower.split())

    def matches_filters(self, filters: Dict[str, Any]) -> bool:
        """過濾條件匹配"""
        if "type" in filters and self.type.value != filters["type"]:
            return False
        if "category" in filters and not self.category.startswith(filters["category"]):
            return False
        if "tags" in filters:
            if not any(tag in self.tags for tag in filters["tags"]):
                return False
        if "metadata" in filters:
            for key, value in filters["metadata"].items():
                if self.metadata.get(key) != value:
                    return False
        return True


@dataclass
class SearchResult:
    """搜尋結果"""
    card: KnowledgeCard
    score: float = 0.0
    highlights: List[str] = field(default_factory=list)
