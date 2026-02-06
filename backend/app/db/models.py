"""
SQLAlchemy Database Models
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import JSON, DateTime, Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class for all models"""
    pass


class Agent(Base):
    """Agent 狀態表"""
    __tablename__ = "agents"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    role: Mapped[str] = mapped_column(String(50))
    status: Mapped[str] = mapped_column(
        String(50), default="idle"
    )  # idle, working, blocked_internal, blocked_user
    current_task_id: Mapped[Optional[str]] = mapped_column(
        String(50), ForeignKey("tasks.id"), nullable=True
    )
    blocking_info: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    last_active_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    current_task = relationship("Task", back_populates="assigned_agent")
    logs = relationship("Log", back_populates="agent")
    ledger_entries = relationship("LedgerEntry", back_populates="agent")


class Task(Base):
    """任務表（含 Pipeline 階段）"""
    __tablename__ = "tasks"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Pipeline info
    pipeline: Mapped[str] = mapped_column(String(20))  # "sales" or "product"
    stage: Mapped[str] = mapped_column(String(50))

    # Assignment
    assigned_to: Mapped[Optional[str]] = mapped_column(
        String(50), ForeignKey("agents.id"), nullable=True
    )

    # For sales pipeline
    company: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    contact_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    contact_email: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    deal_value: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # For product pipeline
    spec: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    artifact_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    staging_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    production_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Metadata
    priority: Mapped[int] = mapped_column(Integer, default=2)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Relationships
    assigned_agent = relationship("Agent", back_populates="current_task")
    logs = relationship("Log", back_populates="task")


class Log(Base):
    """日誌表（對話、狀態轉換、訊息）"""
    __tablename__ = "logs"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    type: Mapped[str] = mapped_column(
        String(50)
    )  # message, pipeline_transition, llm_call, error

    # Context
    agent_id: Mapped[Optional[str]] = mapped_column(
        String(50), ForeignKey("agents.id"), nullable=True
    )
    task_id: Mapped[Optional[str]] = mapped_column(
        String(50), ForeignKey("tasks.id"), nullable=True
    )

    # Message content
    from_agent: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    to_agent: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    subject: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    payload: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    correlation_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Pipeline transition
    from_state: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    to_state: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    agent = relationship("Agent", back_populates="logs")
    task = relationship("Task", back_populates="logs")


class LedgerEntry(Base):
    """財務帳本（LLM Token 計費）"""
    __tablename__ = "ledger"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Context
    agent_id: Mapped[str] = mapped_column(String(50), ForeignKey("agents.id"))
    task_id: Mapped[Optional[str]] = mapped_column(
        String(50), ForeignKey("tasks.id"), nullable=True
    )

    # LLM info
    provider: Mapped[str] = mapped_column(String(20))  # gemini, claude, openai
    model: Mapped[str] = mapped_column(String(50))

    # Token usage
    input_tokens: Mapped[int] = mapped_column(Integer)
    output_tokens: Mapped[int] = mapped_column(Integer)
    cost_usd: Mapped[float] = mapped_column(Float)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    agent = relationship("Agent", back_populates="ledger_entries")


class InboxItem(Base):
    """CEO Inbox（待決策事項）"""
    __tablename__ = "inbox"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    from_agent: Mapped[str] = mapped_column(String(50))
    subject: Mapped[str] = mapped_column(String(200))
    payload: Mapped[dict] = mapped_column(JSON)
    priority: Mapped[int] = mapped_column(Integer, default=2)
    status: Mapped[str] = mapped_column(
        String(20), default="pending"
    )  # pending, approved, rejected
    decision_feedback: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Related entities
    task_id: Mapped[Optional[str]] = mapped_column(
        String(50), ForeignKey("tasks.id"), nullable=True
    )
    message_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    decided_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
