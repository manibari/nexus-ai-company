"""
CEO To-Do Models

CEO 待辦系統資料模型
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4


class TodoPriority(Enum):
    """待辦優先級"""
    URGENT = "urgent"       # 🔴 緊急
    HIGH = "high"           # 🟠 高
    NORMAL = "normal"       # 🟡 一般
    LOW = "low"             # 🟢 低


class TodoType(Enum):
    """待辦類型"""
    APPROVAL = "approval"             # 審批（同意/拒絕）
    QUESTIONNAIRE = "questionnaire"   # 問卷（填寫回覆）
    REVIEW = "review"                 # 審查（通過/退回）
    DECISION = "decision"             # 決策（選擇方案）
    NOTIFICATION = "notification"     # 通知（確認已讀）


class TodoStatus(Enum):
    """待辦狀態"""
    PENDING = "pending"           # 待處理
    IN_PROGRESS = "in_progress"   # 處理中
    COMPLETED = "completed"       # 已完成
    EXPIRED = "expired"           # 已過期


@dataclass
class TodoAction:
    """可執行的動作"""
    id: str
    label: str                           # 按鈕文字
    style: str = "default"               # default, primary, danger
    requires_input: bool = False         # 是否需要輸入
    input_placeholder: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "label": self.label,
            "style": self.style,
            "requires_input": self.requires_input,
            "input_placeholder": self.input_placeholder,
        }


@dataclass
class QuestionItem:
    """問卷題目"""
    id: str
    question: str
    options: Optional[List[str]] = None  # 選項（如有）
    required: bool = True
    answer: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "question": self.question,
            "options": self.options,
            "required": self.required,
            "answer": self.answer,
        }


@dataclass
class TodoItem:
    """CEO 待辦事項"""
    id: str

    # 基本資訊
    project_name: str                    # 專案名稱
    subject: str                         # 待辦事項
    description: Optional[str] = None    # 詳細說明

    # 來源
    from_agent: str = ""                 # 發起的 Agent ID
    from_agent_name: str = ""            # Agent 名稱

    # 分類
    type: TodoType = TodoType.NOTIFICATION
    priority: TodoPriority = TodoPriority.NORMAL

    # 時間
    created_at: datetime = field(default_factory=datetime.utcnow)
    deadline: Optional[datetime] = None  # DDL
    completed_at: Optional[datetime] = None

    # 狀態
    status: TodoStatus = TodoStatus.PENDING

    # 動作
    actions: List[TodoAction] = field(default_factory=list)

    # 回覆（CEO 的回應）
    response: Optional[Dict[str, Any]] = None

    # 關聯
    related_entity_type: Optional[str] = None  # opportunity, product, goal
    related_entity_id: Optional[str] = None

    # 額外資料（問卷題目、審批詳情等）
    payload: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.id:
            timestamp = datetime.now().strftime("%Y%m%d%H%M")
            self.id = f"TODO-{timestamp}-{uuid4().hex[:4].upper()}"

    @property
    def is_overdue(self) -> bool:
        """是否已過期"""
        if self.deadline and self.status == TodoStatus.PENDING:
            return datetime.utcnow() > self.deadline
        return False

    @property
    def priority_order(self) -> int:
        """優先級排序（用於排序）"""
        order = {
            TodoPriority.URGENT: 0,
            TodoPriority.HIGH: 1,
            TodoPriority.NORMAL: 2,
            TodoPriority.LOW: 3,
        }
        return order.get(self.priority, 99)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "project_name": self.project_name,
            "subject": self.subject,
            "description": self.description,
            "from_agent": self.from_agent,
            "from_agent_name": self.from_agent_name,
            "type": self.type.value,
            "priority": self.priority.value,
            "created_at": self.created_at.isoformat(),
            "deadline": self.deadline.isoformat() if self.deadline else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "status": self.status.value,
            "actions": [a.to_dict() for a in self.actions],
            "response": self.response,
            "related_entity_type": self.related_entity_type,
            "related_entity_id": self.related_entity_id,
            "payload": self.payload,
            "is_overdue": self.is_overdue,
        }

    def to_summary(self) -> Dict[str, Any]:
        """簡化摘要"""
        return {
            "id": self.id,
            "project_name": self.project_name,
            "subject": self.subject,
            "from_agent_name": self.from_agent_name,
            "type": self.type.value,
            "priority": self.priority.value,
            "deadline": self.deadline.isoformat() if self.deadline else None,
            "status": self.status.value,
            "is_overdue": self.is_overdue,
        }
