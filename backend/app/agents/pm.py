"""
PM Agent (Product Manager)

負責：
- 接收產品功能需求
- 撰寫 Feature Request
- 設計 PRD (Product Requirements Document)
- 提交 CEO 確認
- 確認後轉交 DEVELOPER Agent

使用 Gemini 2.5 Flash（輕量級任務，非程式碼生成）
"""

import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4

from app.ceo.models import (
    TodoItem,
    TodoAction,
    TodoType,
    TodoPriority,
)
from app.agents.activity_log import ActivityType, get_activity_repo

logger = logging.getLogger(__name__)


class PMAction(Enum):
    """PM 可執行的動作"""
    CREATE_FEATURE_REQUEST = "create_feature_request"
    DRAFT_PRD = "draft_prd"
    SUBMIT_FOR_APPROVAL = "submit_for_approval"
    UPDATE_FEATURE = "update_feature"
    ASSIGN_TO_DEVELOPER = "assign_to_developer"
    PRIORITIZE = "prioritize"
    CLOSE_FEATURE = "close_feature"


class FeatureStatus(Enum):
    """功能需求狀態"""
    DRAFT = "draft"
    AWAITING_APPROVAL = "awaiting_approval"
    APPROVED = "approved"
    IN_DEVELOPMENT = "in_development"
    IN_REVIEW = "in_review"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class FeaturePriority(Enum):
    """功能優先級"""
    P0_CRITICAL = "p0_critical"      # 緊急，立即處理
    P1_HIGH = "p1_high"              # 高優先級，本週完成
    P2_MEDIUM = "p2_medium"          # 中優先級，本月完成
    P3_LOW = "p3_low"                # 低優先級，待排程


@dataclass
class FeatureRequest:
    """功能需求"""
    id: str
    project_name: str
    title: str
    description: str
    user_story: str
    acceptance_criteria: List[str]
    priority: FeaturePriority
    status: FeatureStatus

    # 來源
    source_intake_id: Optional[str] = None
    ceo_input: Optional[str] = None

    # PRD 內容
    prd_summary: str = ""
    technical_requirements: List[str] = field(default_factory=list)
    ui_requirements: List[str] = field(default_factory=list)
    out_of_scope: List[str] = field(default_factory=list)

    # 估算
    estimated_effort: str = ""  # S/M/L/XL
    estimated_days: int = 0

    # 關聯
    related_features: List[str] = field(default_factory=list)
    assigned_to: Optional[str] = None

    # 時間戳
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    approved_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "project_name": self.project_name,
            "title": self.title,
            "description": self.description,
            "user_story": self.user_story,
            "acceptance_criteria": self.acceptance_criteria,
            "priority": self.priority.value,
            "status": self.status.value,
            "source_intake_id": self.source_intake_id,
            "ceo_input": self.ceo_input,
            "prd_summary": self.prd_summary,
            "technical_requirements": self.technical_requirements,
            "ui_requirements": self.ui_requirements,
            "out_of_scope": self.out_of_scope,
            "estimated_effort": self.estimated_effort,
            "estimated_days": self.estimated_days,
            "assigned_to": self.assigned_to,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "approved_at": self.approved_at.isoformat() if self.approved_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


@dataclass
class PMThinkResult:
    """PM 思考結果"""
    action: PMAction
    params: Dict[str, Any]
    reasoning: str
    confidence: float = 0.8
    requires_approval: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "action": self.action.value,
            "params": self.params,
            "reasoning": self.reasoning,
            "confidence": self.confidence,
            "requires_approval": self.requires_approval,
        }


class FeatureRepository:
    """Feature Request 儲存庫（SQLAlchemy 版本）"""

    def __init__(self, session_factory=None):
        self._session_factory = session_factory

    def _session(self):
        return self._session_factory()

    @staticmethod
    def _domain_to_db(feature: 'FeatureRequest') -> 'Feature_DB':
        from app.db.models import Feature as Feature_DB
        return Feature_DB(
            id=feature.id,
            project_name=feature.project_name,
            title=feature.title,
            description=feature.description,
            user_story=feature.user_story,
            acceptance_criteria=feature.acceptance_criteria,
            priority=feature.priority.value,
            status=feature.status.value,
            source_intake_id=feature.source_intake_id,
            ceo_input=feature.ceo_input,
            prd_summary=feature.prd_summary,
            technical_requirements=feature.technical_requirements,
            ui_requirements=feature.ui_requirements,
            out_of_scope=feature.out_of_scope,
            estimated_effort=feature.estimated_effort,
            estimated_days=feature.estimated_days,
            related_features=feature.related_features,
            assigned_to=feature.assigned_to,
            created_at=feature.created_at,
            updated_at=feature.updated_at,
            approved_at=feature.approved_at,
            completed_at=feature.completed_at,
        )

    @staticmethod
    def _db_to_domain(row) -> 'FeatureRequest':
        return FeatureRequest(
            id=row.id,
            project_name=row.project_name,
            title=row.title,
            description=row.description or "",
            user_story=row.user_story or "",
            acceptance_criteria=row.acceptance_criteria or [],
            priority=FeaturePriority(row.priority) if row.priority else FeaturePriority.P2_MEDIUM,
            status=FeatureStatus(row.status) if row.status else FeatureStatus.DRAFT,
            source_intake_id=row.source_intake_id,
            ceo_input=row.ceo_input,
            prd_summary=row.prd_summary or "",
            technical_requirements=row.technical_requirements or [],
            ui_requirements=row.ui_requirements or [],
            out_of_scope=row.out_of_scope or [],
            estimated_effort=row.estimated_effort or "M",
            estimated_days=row.estimated_days or 0,
            related_features=row.related_features or [],
            assigned_to=row.assigned_to,
            created_at=row.created_at,
            updated_at=row.updated_at,
            approved_at=row.approved_at,
            completed_at=row.completed_at,
        )

    async def create(self, feature: FeatureRequest) -> FeatureRequest:
        from app.db.models import Feature as Feature_DB
        if not feature.id:
            feature.id = f"FEAT-{uuid4().hex[:8].upper()}"
        async with self._session() as session:
            db_feat = self._domain_to_db(feature)
            session.add(db_feat)
            await session.commit()
        logger.info(f"Created feature request: {feature.id}")
        return feature

    async def get(self, feature_id: str) -> Optional[FeatureRequest]:
        from app.db.models import Feature as Feature_DB
        async with self._session() as session:
            result = await session.get(Feature_DB, feature_id)
            return self._db_to_domain(result) if result else None

    async def update(self, feature: FeatureRequest) -> FeatureRequest:
        from app.db.models import Feature as Feature_DB
        feature.updated_at = datetime.utcnow()
        async with self._session() as session:
            row = await session.get(Feature_DB, feature.id)
            if not row:
                raise ValueError(f"Feature {feature.id} not found")
            row.project_name = feature.project_name
            row.title = feature.title
            row.description = feature.description
            row.user_story = feature.user_story
            row.acceptance_criteria = feature.acceptance_criteria
            row.priority = feature.priority.value
            row.status = feature.status.value
            row.source_intake_id = feature.source_intake_id
            row.ceo_input = feature.ceo_input
            row.prd_summary = feature.prd_summary
            row.technical_requirements = feature.technical_requirements
            row.ui_requirements = feature.ui_requirements
            row.out_of_scope = feature.out_of_scope
            row.estimated_effort = feature.estimated_effort
            row.estimated_days = feature.estimated_days
            row.related_features = feature.related_features
            row.assigned_to = feature.assigned_to
            row.updated_at = feature.updated_at
            row.approved_at = feature.approved_at
            row.completed_at = feature.completed_at
            await session.commit()
        return feature

    async def list_by_project(self, project_name: str) -> List[FeatureRequest]:
        from sqlalchemy import select
        from app.db.models import Feature as Feature_DB
        async with self._session() as session:
            stmt = select(Feature_DB).where(Feature_DB.project_name == project_name)
            result = await session.execute(stmt)
            return [self._db_to_domain(r) for r in result.scalars().all()]

    async def list_by_status(self, status: FeatureStatus) -> List[FeatureRequest]:
        from sqlalchemy import select
        from app.db.models import Feature as Feature_DB
        async with self._session() as session:
            stmt = select(Feature_DB).where(Feature_DB.status == status.value)
            result = await session.execute(stmt)
            return [self._db_to_domain(r) for r in result.scalars().all()]

    async def list_all(self) -> List[FeatureRequest]:
        from sqlalchemy import select
        from app.db.models import Feature as Feature_DB
        async with self._session() as session:
            stmt = select(Feature_DB).order_by(Feature_DB.created_at.desc())
            result = await session.execute(stmt)
            return [self._db_to_domain(r) for r in result.scalars().all()]


class PMAgent:
    """
    PM Agent - 產品經理

    職責：
    1. 從 GATEKEEPER 接收產品功能需求
    2. 使用 Gemini 分析並撰寫 PRD
    3. 建立 Feature Request
    4. 提交 CEO 確認
    5. 確認後分派給 DEVELOPER
    """

    # 已知專案
    KNOWN_PROJECTS = {
        "stockpulse": {
            "name": "StockPulse",
            "description": "美股分析軟體",
            "tech_stack": ["FastAPI", "React", "TradingView Charts", "yfinance"],
        },
        "nexus": {
            "name": "Nexus AI Company",
            "description": "AI Agent 系統",
            "tech_stack": ["FastAPI", "React", "Gemini", "Claude"],
        },
    }

    def __init__(
        self,
        feature_repo: Optional[FeatureRepository] = None,
        todo_repo=None,
    ):
        self.feature_repo = feature_repo or FeatureRepository()
        self.todo_repo = todo_repo  # 延遲取得，避免循環引用
        self.id = "PM"
        self.name = "Product Manager"
        self._gemini_client = None

    @property
    def agent_id(self) -> str:
        return "PM"

    @property
    def agent_name(self) -> str:
        return "Product Manager"

    async def handle(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """AgentHandler 介面實作"""
        content = payload.get("content", "")
        entities = payload.get("entities", [])
        intake_id = payload.get("intake_id")
        return await self.process_feature_request(content, entities, intake_id)

    def _get_todo_repo(self):
        """延遲取得 Todo Repository（避免循環引用）"""
        if self.todo_repo is None:
            from app.api.ceo_todo import _get_repo
            self.todo_repo = _get_repo()
        return self.todo_repo

    def _get_gemini(self):
        """延遲初始化 Gemini client"""
        if self._gemini_client is None:
            import google.generativeai as genai
            api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
            if not api_key:
                logger.warning("No Gemini API key found")
                return None
            genai.configure(api_key=api_key)
            self._gemini_client = genai.GenerativeModel("gemini-2.5-flash")
        return self._gemini_client

    async def process_feature_request(
        self,
        content: str,
        entities: List[Dict],
        intake_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        處理從 GATEKEEPER 來的功能需求

        Args:
            content: CEO 原始輸入
            entities: 解析出的實體
            intake_id: 來源 Intake ID

        Returns:
            處理結果，包含 Feature Request 和 PRD
        """
        # 記錄活動開始
        activity_repo = get_activity_repo()
        await activity_repo.log(
            agent_id="PM",
            agent_name="Product Manager",
            activity_type=ActivityType.TASK_START,
            message=f"處理功能需求: {content[:50]}...",
            metadata={"intake_id": intake_id},
        )

        # 1. 識別專案
        project_name = self._identify_project(content, entities)

        # 2. 使用 Gemini 分析需求並生成 PRD
        prd = await self._generate_prd(content, project_name)

        # 3. 建立 Feature Request
        feature = FeatureRequest(
            id="",
            project_name=project_name,
            title=prd.get("title", "新功能"),
            description=prd.get("description", content),
            user_story=prd.get("user_story", ""),
            acceptance_criteria=prd.get("acceptance_criteria", []),
            priority=self._determine_priority(prd),
            status=FeatureStatus.AWAITING_APPROVAL,
            source_intake_id=intake_id,
            ceo_input=content,
            prd_summary=prd.get("summary", ""),
            technical_requirements=prd.get("technical_requirements", []),
            ui_requirements=prd.get("ui_requirements", []),
            out_of_scope=prd.get("out_of_scope", []),
            estimated_effort=prd.get("estimated_effort", "M"),
            estimated_days=prd.get("estimated_days", 3),
        )

        # 4. 儲存
        feature = await self.feature_repo.create(feature)

        # 5. 建立 CEO Todo（整合到 CEO Todo 列表）
        todo = await self._create_ceo_todo(feature)

        # 記錄活動完成
        await activity_repo.log(
            agent_id="PM",
            agent_name="Product Manager",
            activity_type=ActivityType.TASK_END,
            message=f"已建立 PRD: {feature.title}",
            project_name=project_name,
            metadata={
                "feature_id": feature.id,
                "priority": feature.priority.value,
                "estimated_days": feature.estimated_days,
            },
        )

        # 記錄 milestone
        await activity_repo.log(
            agent_id="PM",
            agent_name="Product Manager",
            activity_type=ActivityType.MILESTONE,
            message=f"Feature {feature.id} 待 CEO 審批",
            project_name=project_name,
            metadata={"feature_id": feature.id, "status": "awaiting_approval"},
        )

        return {
            "status": "awaiting_approval",
            "feature": feature.to_dict(),
            "prd": prd,
            "todo": todo.to_dict() if todo else None,
            "message": f"已建立功能需求 {feature.id}，待 CEO 確認",
        }

    async def _generate_prd(
        self,
        content: str,
        project_name: str,
    ) -> Dict[str, Any]:
        """使用 Gemini 生成 PRD"""
        gemini = self._get_gemini()

        # 取得專案資訊
        project_info = self.KNOWN_PROJECTS.get(project_name.lower(), {})
        tech_stack = ", ".join(project_info.get("tech_stack", []))

        if not gemini:
            # Fallback: 簡單解析
            return {
                "title": f"{project_name} 功能優化",
                "description": content,
                "summary": content,
                "user_story": f"作為用戶，我希望 {content}",
                "acceptance_criteria": ["功能正常運作", "UI 符合設計規範"],
                "technical_requirements": [],
                "ui_requirements": [],
                "out_of_scope": [],
                "estimated_effort": "M",
                "estimated_days": 3,
            }

        prompt = f"""你是 {project_name} 專案的 PM。根據 CEO 需求，撰寫功能規格文件。

## CEO 需求
{content}

## 專案資訊
- 名稱: {project_info.get('name', project_name)}
- 描述: {project_info.get('description', '')}
- 技術棧: {tech_stack}

## 輸出格式（純 JSON）
{{
  "title": "功能標題（簡潔）",
  "description": "功能描述（1-2 句）",
  "summary": "PRD 摘要（3-5 句，說明為什麼需要這個功能、預期效果）",
  "user_story": "作為 [用戶角色]，我希望 [功能]，以便 [價值]",
  "acceptance_criteria": [
    "驗收標準 1",
    "驗收標準 2",
    "驗收標準 3"
  ],
  "technical_requirements": [
    "技術需求 1（API/後端）",
    "技術需求 2"
  ],
  "ui_requirements": [
    "UI 需求 1（前端/介面）",
    "UI 需求 2"
  ],
  "out_of_scope": [
    "不在範圍內的項目"
  ],
  "estimated_effort": "S/M/L/XL",
  "estimated_days": 3
}}

注意：
1. 從 CEO 簡短需求中推斷完整規格
2. 技術需求要具體可執行
3. 估算要務實（S=1天, M=3天, L=5天, XL=10天+）
"""

        try:
            response = gemini.generate_content(prompt)
            text = response.text.strip()

            # 清理 markdown
            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
            text = text.strip()

            return json.loads(text)

        except Exception as e:
            logger.error(f"Gemini PRD generation failed: {e}")
            return {
                "title": f"{project_name} 功能需求",
                "description": content,
                "summary": content,
                "user_story": f"作為用戶，我希望 {content}",
                "acceptance_criteria": ["功能正常運作"],
                "technical_requirements": [],
                "ui_requirements": [],
                "out_of_scope": [],
                "estimated_effort": "M",
                "estimated_days": 3,
            }

    def _identify_project(
        self,
        content: str,
        entities: List[Dict],
    ) -> str:
        """識別相關專案"""
        # 從實體中尋找
        for entity in entities:
            if entity.get("entity_type") == "project":
                return entity.get("value", "")

        # 從內容中推斷
        content_lower = content.lower()

        if any(kw in content_lower for kw in ["股票", "stock", "stockpulse", "大盤", "k線"]):
            return "StockPulse"

        if any(kw in content_lower for kw in ["agent", "nexus", "公司系統"]):
            return "Nexus AI Company"

        return "Unknown"

    def _determine_priority(self, prd: Dict) -> FeaturePriority:
        """決定優先級"""
        effort = prd.get("estimated_effort", "M")

        # 簡單邏輯：小任務高優先，大任務需要規劃
        if effort == "S":
            return FeaturePriority.P1_HIGH
        elif effort == "M":
            return FeaturePriority.P2_MEDIUM
        else:
            return FeaturePriority.P3_LOW

    async def _create_ceo_todo(self, feature: FeatureRequest) -> Optional[TodoItem]:
        """建立 CEO 確認 Todo（整合到 CEO Todo 列表）"""
        try:
            todo_repo = self._get_todo_repo()

            # 建立 TodoItem
            todo = TodoItem(
                id="",  # 自動生成
                project_name=feature.project_name,
                subject=f"[PM] 功能需求確認: {feature.title}",
                description=f"""專案: {feature.project_name}
功能: {feature.title}

{feature.prd_summary}

User Story:
{feature.user_story}

驗收標準:
{chr(10).join(f'- {c}' for c in feature.acceptance_criteria)}

估算: {feature.estimated_effort} ({feature.estimated_days} 天)""",
                from_agent=self.id,
                from_agent_name=self.name,
                type=TodoType.APPROVAL,
                priority=TodoPriority.HIGH,
                actions=[
                    TodoAction(id="approve", label="批准開發", style="primary"),
                    TodoAction(
                        id="modify",
                        label="需要修改",
                        style="default",
                        requires_input=True,
                        input_placeholder="請輸入修改意見",
                    ),
                    TodoAction(id="reject", label="取消", style="danger"),
                ],
                related_entity_type="feature",
                related_entity_id=feature.id,
                payload={
                    "feature_id": feature.id,
                    "feature": feature.to_dict(),
                    "callback_endpoint": f"/api/v1/pm/features/{feature.id}/decision",
                },
            )

            await todo_repo.create(todo)
            logger.info(f"Created CEO Todo for feature {feature.id}: {todo.id}")
            return todo

        except Exception as e:
            logger.error(f"Failed to create CEO Todo: {e}")
            return None

    def _create_approval_todo(self, feature: FeatureRequest) -> Dict[str, Any]:
        """建立 CEO 確認 Todo（舊版，保留相容）"""
        return {
            "subject": f"[PM] 功能需求確認: {feature.title}",
            "description": f"""
專案: {feature.project_name}
功能: {feature.title}

{feature.prd_summary}

User Story:
{feature.user_story}

驗收標準:
{chr(10).join(f'- {c}' for c in feature.acceptance_criteria)}

估算: {feature.estimated_effort} ({feature.estimated_days} 天)
""".strip(),
            "from_agent": self.id,
            "from_agent_name": self.name,
            "type": "approval",
            "priority": "normal",
            "actions": [
                {"id": "approve", "label": "批准開發", "style": "primary"},
                {"id": "modify", "label": "需要修改", "style": "default"},
                {"id": "reject", "label": "取消", "style": "danger"},
            ],
            "payload": {
                "feature_id": feature.id,
                "feature": feature.to_dict(),
            },
            "callback_endpoint": f"/api/v1/pm/features/{feature.id}/decision",
        }

    async def handle_ceo_decision(
        self,
        feature_id: str,
        action: str,
        feedback: Optional[str] = None,
    ) -> Dict[str, Any]:
        """處理 CEO 決策回覆"""
        activity_repo = get_activity_repo()
        feature = await self.feature_repo.get(feature_id)
        if not feature:
            return {"error": "Feature not found"}

        # 記錄 CEO 決策
        await activity_repo.log(
            agent_id="PM",
            agent_name="Product Manager",
            activity_type=ActivityType.MESSAGE,
            message=f"收到 CEO 決策: {action}",
            project_name=feature.project_name,
            metadata={"feature_id": feature_id, "action": action, "feedback": feedback},
        )

        if action == "approve":
            feature.status = FeatureStatus.APPROVED
            feature.approved_at = datetime.utcnow()
            await self.feature_repo.update(feature)

            # 記錄批准里程碑
            await activity_repo.log(
                agent_id="PM",
                agent_name="Product Manager",
                activity_type=ActivityType.MILESTONE,
                message=f"Feature {feature_id} CEO 批准",
                project_name=feature.project_name,
                metadata={"feature_id": feature_id},
            )

            # 分派給 DEVELOPER
            developer_task = await self._assign_to_developer(feature)

            # 記錄分派任務
            await activity_repo.log(
                agent_id="DEVELOPER",
                agent_name="Developer Agent",
                activity_type=ActivityType.TASK_START,
                message=f"開始開發: {feature.title}",
                project_name=feature.project_name,
                metadata={
                    "feature_id": feature_id,
                    "task_id": developer_task.get("id"),
                    "estimated_days": feature.estimated_days,
                },
            )

            return {
                "status": "approved",
                "feature": feature.to_dict(),
                "developer_task": developer_task,
                "message": f"功能 {feature.id} 已批准，已分派給 DEVELOPER",
            }

        elif action == "modify":
            feature.status = FeatureStatus.DRAFT
            if feedback:
                feature.description += f"\n\n[CEO 反饋] {feedback}"
            await self.feature_repo.update(feature)

            return {
                "status": "needs_modification",
                "feature": feature.to_dict(),
                "message": "功能需求需要修改",
            }

        elif action == "reject":
            feature.status = FeatureStatus.CANCELLED
            await self.feature_repo.update(feature)

            return {
                "status": "cancelled",
                "feature": feature.to_dict(),
                "message": "功能需求已取消",
            }

        return {"error": f"Unknown action: {action}"}

    async def _assign_to_developer(self, feature: FeatureRequest) -> Dict[str, Any]:
        """分派給 DEVELOPER Agent，並建立 ProductItem 進入 Product Board"""
        feature.status = FeatureStatus.IN_DEVELOPMENT
        feature.assigned_to = "DEVELOPER"
        await self.feature_repo.update(feature)

        # 建立開發任務
        task = {
            "id": f"DEV-{feature.id}",
            "type": "feature_implementation",
            "feature_id": feature.id,
            "project": feature.project_name,
            "title": feature.title,
            "description": feature.description,
            "requirements": {
                "technical": feature.technical_requirements,
                "ui": feature.ui_requirements,
                "acceptance_criteria": feature.acceptance_criteria,
            },
            "priority": feature.priority.value,
            "estimated_days": feature.estimated_days,
            "assigned_at": datetime.utcnow().isoformat(),
        }

        logger.info(f"Assigned {feature.id} to DEVELOPER: {task['id']}")

        # === Feature → ProductItem Bridge ===
        product_item = await self._create_product_item(feature)
        if product_item:
            task["product_item_id"] = product_item.id

        return task

    async def _create_product_item(self, feature: FeatureRequest) -> Optional[Any]:
        """從 Feature 建立 ProductItem，放入 Product Board Pipeline"""
        from app.product.repository import get_product_repo
        from app.product.models import (
            ProductItem,
            ProductStage,
            ProductPriority,
            ProductType,
        )

        try:
            repo = get_product_repo()

            # Priority 對應: Feature P0~P3 → ProductItem critical~low
            priority_map = {
                FeaturePriority.P0_CRITICAL: ProductPriority.CRITICAL,
                FeaturePriority.P1_HIGH: ProductPriority.HIGH,
                FeaturePriority.P2_MEDIUM: ProductPriority.MEDIUM,
                FeaturePriority.P3_LOW: ProductPriority.LOW,
            }

            # 組合 spec_doc (PRD summary + technical + UI requirements)
            spec_parts = []
            if feature.prd_summary:
                spec_parts.append(f"## PRD Summary\n{feature.prd_summary}")
            if feature.technical_requirements:
                spec_parts.append(
                    "## Technical Requirements\n"
                    + "\n".join(f"- {r}" for r in feature.technical_requirements)
                )
            if feature.ui_requirements:
                spec_parts.append(
                    "## UI Requirements\n"
                    + "\n".join(f"- {r}" for r in feature.ui_requirements)
                )
            spec_doc = "\n\n".join(spec_parts) if spec_parts else None

            product_item = ProductItem(
                id="",  # auto-generate PROD-2026-XXXX
                title=feature.title,
                description=feature.description,
                type=ProductType.FEATURE,
                priority=priority_map.get(feature.priority, ProductPriority.MEDIUM),
                stage=ProductStage.P2_SPEC_READY,  # PRD 已完成，跳過 backlog
                spec_doc=spec_doc,
                acceptance_criteria=feature.acceptance_criteria,
                assignee="DEVELOPER",
                estimated_hours=feature.estimated_days * 8 if feature.estimated_days else None,
                source_input_id=feature.id,  # 回溯連結
                tags=[feature.project_name] if feature.project_name else [],
            )

            await repo.create(product_item)
            logger.info(
                f"Created ProductItem {product_item.id} from Feature {feature.id} (spec_ready)"
            )

            # Activity Log: MILESTONE
            activity_repo = get_activity_repo()
            await activity_repo.log(
                agent_id="PM",
                agent_name="Product Manager",
                activity_type=ActivityType.MILESTONE,
                message=f"Feature {feature.id} → ProductItem {product_item.id} (spec_ready)",
                project_name=feature.project_name,
                metadata={
                    "feature_id": feature.id,
                    "product_item_id": product_item.id,
                    "stage": "spec_ready",
                },
            )

            return product_item

        except Exception as e:
            logger.error(f"Failed to create ProductItem from Feature {feature.id}: {e}")
            return None

    async def get_feature(self, feature_id: str) -> Optional[Dict[str, Any]]:
        """取得功能需求詳情"""
        feature = await self.feature_repo.get(feature_id)
        return feature.to_dict() if feature else None

    async def list_features(
        self,
        project: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """列出功能需求"""
        if status:
            features = await self.feature_repo.list_by_status(FeatureStatus(status))
        elif project:
            features = await self.feature_repo.list_by_project(project)
        else:
            features = await self.feature_repo.list_all()

        return [f.to_dict() for f in features]


# 全域共享儲存庫
_feature_repo = None
_pm = None


def get_pm_agent() -> PMAgent:
    """取得共享的 PM Agent 實例"""
    global _pm, _feature_repo
    if _pm is None:
        from app.db.database import AsyncSessionLocal
        _feature_repo = FeatureRepository(session_factory=AsyncSessionLocal)
        _pm = PMAgent(feature_repo=_feature_repo)
    return _pm


async def process_feature(content: str, entities: List[Dict], intake_id: str = None) -> Dict:
    """便利函數：處理功能需求"""
    pm = get_pm_agent()
    return await pm.process_feature_request(content, entities, intake_id)


async def handle_decision(feature_id: str, action: str, feedback: str = None) -> Dict:
    """便利函數：處理 CEO 決策"""
    pm = get_pm_agent()
    return await pm.handle_ceo_decision(feature_id, action, feedback)


async def get_feature(feature_id: str) -> Optional[Dict]:
    """便利函數：取得功能需求"""
    pm = get_pm_agent()
    return await pm.get_feature(feature_id)
