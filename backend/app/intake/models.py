"""
CEO Intake Data Models
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class InputType(Enum):
    """輸入類型"""
    TEXT = "text"              # 純文字
    EMAIL = "email"            # 轉發的 Email
    URL = "url"                # 網址連結
    VOICE = "voice"            # 語音輸入
    IMAGE = "image"            # 圖片（名片等）
    DOCUMENT = "document"      # 文件


class InputIntent(Enum):
    """意圖分類"""
    OPPORTUNITY = "opportunity"  # 潛在商機 → HUNTER
    PROJECT = "project"          # 專案需求 → ORCHESTRATOR
    QUESTION = "question"        # 問題詢問 → 直接回覆
    TASK = "task"                # 待辦事項 → 建立任務
    INFO = "info"                # 資訊分享 → 記錄存檔
    UNKNOWN = "unknown"          # 無法識別


class InputStatus(Enum):
    """處理狀態"""
    PENDING = "pending"                      # 待處理
    PROCESSING = "processing"                # 處理中
    AWAITING_CONFIRMATION = "awaiting_confirmation"  # 待 CEO 確認
    CONFIRMED = "confirmed"                  # 已確認
    REJECTED = "rejected"                    # 已拒絕
    COMPLETED = "completed"                  # 已完成
    FAILED = "failed"                        # 處理失敗


@dataclass
class ParsedEntity:
    """解析出的實體"""
    entity_type: str   # company, person, amount, date, product, etc.
    value: str
    confidence: float
    context: str = ""  # 原文中的上下文


@dataclass
class EnrichedData:
    """補全的資訊"""
    company_info: Optional[Dict[str, Any]] = None
    contact_info: Optional[Dict[str, Any]] = None
    industry_info: Optional[Dict[str, Any]] = None
    news: Optional[List[Dict[str, Any]]] = None
    linkedin_profiles: Optional[List[Dict[str, Any]]] = None
    source_urls: List[str] = field(default_factory=list)


@dataclass
class StructuredOpportunity:
    """結構化的商機"""
    company_name: str
    industry: Optional[str] = None
    company_size: Optional[str] = None
    region: Optional[str] = None

    contact_name: Optional[str] = None
    contact_title: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None

    opportunity_type: str = "general"  # partnership, sales, investment
    estimated_value: Optional[float] = None
    urgency: str = "normal"  # low, normal, high, urgent

    source: str = "ceo_referral"
    ceo_notes: str = ""
    next_steps: List[str] = field(default_factory=list)

    def to_lead_data(self) -> Dict[str, Any]:
        """轉換為 Lead 建立資料"""
        return {
            "company": self.company_name,
            "industry": self.industry,
            "contact_name": self.contact_name,
            "contact_email": self.contact_email,
            "source_type": "ceo_referral",
            "priority": "high" if self.urgency in ["high", "urgent"] else "normal",
            "notes": self.ceo_notes,
            "deal_value": self.estimated_value,
        }


@dataclass
class CEOInput:
    """
    CEO 輸入記錄

    完整記錄 CEO 的輸入從原始內容到最終處理結果的全過程
    """
    id: str

    # 原始輸入
    raw_content: str
    input_type: InputType = InputType.TEXT
    source: str = "web"  # web, slack, email, api, voice
    attachments: List[str] = field(default_factory=list)

    # 解析結果
    intent: InputIntent = InputIntent.UNKNOWN
    intent_confidence: float = 0.0
    parsed_entities: List[ParsedEntity] = field(default_factory=list)
    enriched_data: Optional[EnrichedData] = None

    # 結構化結果
    structured_data: Optional[Dict[str, Any]] = None
    structured_opportunity: Optional[StructuredOpportunity] = None

    # 路由結果
    routed_to: Optional[str] = None  # HUNTER, ORCHESTRATOR, None
    created_entity_type: Optional[str] = None  # lead, task
    created_entity_id: Optional[str] = None

    # CEO 確認
    requires_confirmation: bool = True
    ceo_confirmed: Optional[bool] = None
    ceo_feedback: Optional[str] = None
    ceo_modifications: Optional[Dict[str, Any]] = None

    # 處理狀態
    status: InputStatus = InputStatus.PENDING
    error_message: Optional[str] = None

    # 處理摘要（給 CEO 看的）
    summary: Optional[str] = None
    suggested_actions: List[str] = field(default_factory=list)

    # 時間戳
    created_at: datetime = field(default_factory=datetime.utcnow)
    processed_at: Optional[datetime] = None
    confirmed_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "raw_content": self.raw_content,
            "input_type": self.input_type.value,
            "source": self.source,
            "intent": self.intent.value,
            "intent_confidence": self.intent_confidence,
            "status": self.status.value,
            "summary": self.summary,
            "suggested_actions": self.suggested_actions,
            "requires_confirmation": self.requires_confirmation,
            "ceo_confirmed": self.ceo_confirmed,
            "routed_to": self.routed_to,
            "created_entity_id": self.created_entity_id,
            "created_at": self.created_at.isoformat(),
        }

    def to_confirmation_card(self) -> Dict[str, Any]:
        """生成給 CEO 確認的卡片"""
        card = {
            "id": self.id,
            "type": "intake_confirmation",
            "original_input": self.raw_content[:200] + "..." if len(self.raw_content) > 200 else self.raw_content,
            "interpretation": {
                "intent": self.intent.value,
                "confidence": f"{self.intent_confidence * 100:.0f}%",
            },
            "summary": self.summary,
            "suggested_actions": self.suggested_actions,
        }

        if self.structured_opportunity:
            card["opportunity"] = {
                "company": self.structured_opportunity.company_name,
                "contact": self.structured_opportunity.contact_name,
                "type": self.structured_opportunity.opportunity_type,
                "urgency": self.structured_opportunity.urgency,
            }

        card["actions"] = [
            {"id": "confirm", "label": "✓ 確認並執行"},
            {"id": "modify", "label": "✎ 修改"},
            {"id": "reject", "label": "✗ 取消"},
        ]

        return card
