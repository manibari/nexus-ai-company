"""
HUNTER Agent

負責：
- 商機追蹤與管理
- MEDDIC 分析與更新
- 銷售階段推進
- 客戶互動記錄
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from app.engines.meddic.engine import MEDDICEngine
from app.pipeline.models import (
    Opportunity,
    OpportunityStage,
    OpportunityStatus,
    Contact,
    ContactRole,
    Activity,
    ActivityType,
    MEDDICScore,
)
from app.pipeline.repository import PipelineRepository


class HunterAction(Enum):
    """HUNTER 可執行的動作"""
    CREATE_OPPORTUNITY = "create_opportunity"
    UPDATE_MEDDIC = "update_meddic"
    ADD_CONTACT = "add_contact"
    LOG_ACTIVITY = "log_activity"
    ADVANCE_STAGE = "advance_stage"
    SUGGEST_NEXT_ACTION = "suggest_next_action"
    QUALIFY_LEAD = "qualify_lead"
    MARK_WON = "mark_won"
    MARK_LOST = "mark_lost"


@dataclass
class HunterThinkResult:
    """HUNTER 思考結果"""
    action: HunterAction
    params: Dict[str, Any]
    reasoning: str
    confidence: float = 0.8
    requires_approval: bool = False
    suggested_next_steps: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "action": self.action.value,
            "params": self.params,
            "reasoning": self.reasoning,
            "confidence": self.confidence,
            "requires_approval": self.requires_approval,
            "suggested_next_steps": self.suggested_next_steps,
        }


class HunterAgent:
    """
    HUNTER Agent - 銷售專員

    職責：
    1. 從 GATEKEEPER 接收商機
    2. 進行 MEDDIC 分析
    3. 推進銷售階段
    4. 記錄客戶互動
    5. 建議下一步動作
    """

    def __init__(
        self,
        pipeline_repo: Optional[PipelineRepository] = None,
        meddic_engine: Optional[MEDDICEngine] = None,
    ):
        self.pipeline = pipeline_repo or PipelineRepository()
        self.meddic_engine = meddic_engine or MEDDICEngine()
        self.id = "HUNTER"
        self.name = "Sales Agent"

    @property
    def agent_id(self) -> str:
        return "HUNTER"

    @property
    def agent_name(self) -> str:
        return "Sales Agent"

    async def handle(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """AgentHandler 介面實作"""
        content = payload.get("content", "")
        raw_entities = payload.get("entities", [])
        # 標準化 entity 格式：GATEKEEPER 用 entity_type，但 process_intake 用 type
        entities = [
            {"type": e.get("entity_type", e.get("type")), "value": e.get("value"),
             "metadata": e.get("metadata", {})}
            for e in raw_entities
        ]
        meddic_analysis = payload.get("meddic_analysis")
        return await self.process_intake(content, entities, meddic_analysis)

    async def process_intake(
        self,
        content: str,
        entities: List[Dict],
        meddic_analysis: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """
        處理從 GATEKEEPER 來的商機

        Args:
            content: 原始輸入內容
            entities: 解析出的實體
            meddic_analysis: MEDDIC 分析結果

        Returns:
            處理結果，包含建立的商機和建議
        """
        # 1. 從實體中提取資訊
        company = self._extract_company(entities)
        contacts = self._extract_contacts(entities)
        amount = self._extract_amount(entities)

        # 2. 建立商機
        meddic_score = self._build_meddic_score(meddic_analysis) if meddic_analysis else MEDDICScore()

        opp = Opportunity(
            id="",
            name=f"{company} 商機" if company else "新商機",
            company=company or "Unknown",
            amount=amount,
            source="ceo_intake",
            source_detail=content[:100],
            meddic=meddic_score,
        )

        # 加入聯絡人
        for contact_data in contacts:
            contact = Contact(
                id="",
                name=contact_data.get("name", "Unknown"),
                title=contact_data.get("title"),
                role=self._determine_contact_role(contact_data),
            )
            opp.contacts.append(contact)

            # 更新 MEDDIC
            if contact.role == ContactRole.CHAMPION:
                opp.meddic.champion_identified = True
                opp.meddic.champion_name = contact.name
                opp.meddic.champion_title = contact.title
                opp.meddic.champion_score = max(opp.meddic.champion_score, 5)
            elif contact.role == ContactRole.ECONOMIC_BUYER:
                opp.meddic.eb_identified = True
                opp.meddic.eb_name = contact.name
                opp.meddic.eb_score = max(opp.meddic.eb_score, 3)
                opp.meddic.eb_access_level = "identified"

        # 3. 儲存
        await self.pipeline.create_opportunity(opp)

        # 4. 生成建議
        suggestions = self._generate_suggestions(opp)

        return {
            "status": "created",
            "opportunity": opp.to_dict(),
            "suggestions": suggestions,
            "next_steps": opp.meddic.get_next_actions(),
        }

    async def analyze_opportunity(self, opp_id: str) -> Dict[str, Any]:
        """
        分析商機狀態並提供建議

        Args:
            opp_id: 商機 ID

        Returns:
            分析結果和建議
        """
        opp = await self.pipeline.get_opportunity(opp_id)
        if not opp:
            return {"error": "Opportunity not found"}

        # 重新分析 MEDDIC
        analysis = {
            "opportunity": opp.to_summary(),
            "meddic": opp.meddic.to_dict(),
            "health": opp.meddic.health,
            "gaps": opp.meddic.get_gaps(),
            "next_actions": opp.meddic.get_next_actions(),
            "stage_analysis": self._analyze_stage_readiness(opp),
            "risk_factors": self._identify_risks(opp),
        }

        return analysis

    async def suggest_action(self, opp_id: str) -> HunterThinkResult:
        """
        為特定商機建議下一步動作

        Args:
            opp_id: 商機 ID

        Returns:
            建議的動作
        """
        opp = await self.pipeline.get_opportunity(opp_id)
        if not opp:
            return HunterThinkResult(
                action=HunterAction.SUGGEST_NEXT_ACTION,
                params={},
                reasoning="Opportunity not found",
                confidence=0.0,
            )

        # 基於 MEDDIC 和階段決定動作
        meddic = opp.meddic
        stage = opp.stage

        # 決策邏輯
        if not meddic.pain_identified:
            return HunterThinkResult(
                action=HunterAction.LOG_ACTIVITY,
                params={
                    "type": "meeting",
                    "subject": "Discovery Call",
                    "objective": "了解客戶痛點",
                },
                reasoning="痛點尚未確認，需要進行 Discovery Call",
                confidence=0.9,
                suggested_next_steps=[
                    "準備 Discovery 問題清單",
                    "了解客戶目前的解決方案",
                    "量化痛點的商業影響",
                ],
            )

        if not meddic.champion_identified:
            return HunterThinkResult(
                action=HunterAction.ADD_CONTACT,
                params={
                    "role": "champion",
                    "objective": "找到內部支持者",
                },
                reasoning="尚未找到 Champion，需要識別內部支持者",
                confidence=0.85,
                suggested_next_steps=[
                    "確認誰最積極推動這個專案",
                    "了解對方的個人利益",
                    "建立信任關係",
                ],
            )

        if meddic.eb_access_level in ["unknown", "identified"]:
            return HunterThinkResult(
                action=HunterAction.LOG_ACTIVITY,
                params={
                    "type": "task",
                    "subject": "安排與 Economic Buyer 會議",
                    "via": "champion",
                },
                reasoning="需要透過 Champion 接觸 Economic Buyer",
                confidence=0.85,
                suggested_next_steps=[
                    "請 Champion 協助安排會議",
                    "準備針對 EB 的價值主張",
                    "了解 EB 的決策標準",
                ],
            )

        if meddic.total_score >= 60 and stage == OpportunityStage.DISCOVERY:
            return HunterThinkResult(
                action=HunterAction.ADVANCE_STAGE,
                params={"target_stage": "proposal"},
                reasoning=f"MEDDIC 分數 {meddic.total_score} 達標，可以進入提案階段",
                confidence=0.8,
                requires_approval=True,
                suggested_next_steps=[
                    "準備正式提案",
                    "確認報價",
                    "安排提案會議",
                ],
            )

        if meddic.total_score >= 70 and stage == OpportunityStage.PROPOSAL:
            return HunterThinkResult(
                action=HunterAction.ADVANCE_STAGE,
                params={"target_stage": "negotiation"},
                reasoning="提案已送出，進入議價階段",
                confidence=0.75,
                suggested_next_steps=[
                    "準備議價策略",
                    "了解競爭對手報價",
                    "準備合約條款",
                ],
            )

        # 預設：持續跟進
        return HunterThinkResult(
            action=HunterAction.LOG_ACTIVITY,
            params={
                "type": "call",
                "subject": "Follow-up",
                "objective": "維持關係並了解進展",
            },
            reasoning="持續跟進，維護客戶關係",
            confidence=0.7,
            suggested_next_steps=[
                "詢問是否有新的需求",
                "分享相關案例或資訊",
                "確認決策時程",
            ],
        )

    async def execute_action(
        self,
        opp_id: str,
        action: HunterAction,
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        執行動作

        Args:
            opp_id: 商機 ID
            action: 要執行的動作
            params: 動作參數

        Returns:
            執行結果
        """
        opp = await self.pipeline.get_opportunity(opp_id)
        if not opp:
            return {"error": "Opportunity not found"}

        if action == HunterAction.UPDATE_MEDDIC:
            result = await self.pipeline.update_meddic(opp_id, params)
            return {"status": "updated", "meddic": result.to_dict() if result else None}

        elif action == HunterAction.ADD_CONTACT:
            contact = Contact(
                id="",
                name=params.get("name", "Unknown"),
                title=params.get("title"),
                role=ContactRole(params.get("role", "contact")),
                email=params.get("email"),
            )
            result = await self.pipeline.add_contact(opp_id, contact)
            return {"status": "added", "contact": result.to_dict() if result else None}

        elif action == HunterAction.LOG_ACTIVITY:
            activity = Activity(
                id="",
                opportunity_id=opp_id,
                type=ActivityType(params.get("type", "note")),
                subject=params.get("subject", "Activity"),
                summary=params.get("summary"),
                next_action=params.get("next_action"),
                created_by=self.id,
            )
            result = await self.pipeline.add_activity(activity)
            return {"status": "logged", "activity": result.to_dict()}

        elif action == HunterAction.ADVANCE_STAGE:
            result = await self.pipeline.advance_stage(opp_id)
            if result:
                return {"status": "advanced", "new_stage": result.stage.value}
            return {"status": "failed", "reason": "Cannot advance stage"}

        elif action == HunterAction.MARK_WON:
            result = await self.pipeline.mark_won(opp_id)
            return {"status": "won", "opportunity": result.to_dict() if result else None}

        elif action == HunterAction.MARK_LOST:
            reason = params.get("reason")
            result = await self.pipeline.mark_lost(opp_id, reason)
            return {"status": "lost", "opportunity": result.to_dict() if result else None}

        return {"error": f"Unknown action: {action}"}

    def _extract_company(self, entities: List[Dict]) -> Optional[str]:
        """從實體中提取公司名稱"""
        for entity in entities:
            if entity.get("type") == "company":
                return entity.get("value")
        return None

    def _extract_contacts(self, entities: List[Dict]) -> List[Dict]:
        """從實體中提取聯絡人"""
        contacts = []
        for entity in entities:
            if entity.get("type") == "person":
                contacts.append({
                    "name": entity.get("value"),
                    "title": entity.get("metadata", {}).get("title"),
                    "level": entity.get("metadata", {}).get("level"),
                })
        return contacts

    def _extract_amount(self, entities: List[Dict]) -> Optional[float]:
        """從實體中提取金額"""
        for entity in entities:
            if entity.get("type") == "amount":
                try:
                    return float(entity.get("value", 0))
                except ValueError:
                    pass
        return None

    def _determine_contact_role(self, contact_data: Dict) -> ContactRole:
        """判斷聯絡人角色"""
        level = contact_data.get("level", "")
        title = contact_data.get("title", "").lower()

        if level == "c_level" or any(t in title for t in ["ceo", "總經理", "老闆"]):
            return ContactRole.ECONOMIC_BUYER
        elif level in ["vp", "director"]:
            return ContactRole.CHAMPION
        elif "經理" in title or "manager" in title:
            return ContactRole.INFLUENCER
        else:
            return ContactRole.CONTACT

    def _build_meddic_score(self, analysis: Dict) -> MEDDICScore:
        """從分析結果建立 MEDDIC 分數"""
        pain = analysis.get("pain", {})
        champion = analysis.get("champion", {})
        eb = analysis.get("economic_buyer", {})

        return MEDDICScore(
            pain_score=pain.get("score", 0),
            pain_identified=pain.get("identified", False),
            pain_description=pain.get("description"),
            champion_score=champion.get("score", 0),
            champion_identified=champion.get("identified", False),
            champion_name=champion.get("name"),
            champion_title=champion.get("title"),
            eb_score=eb.get("score", 0),
            eb_identified=eb.get("identified", False),
            eb_name=eb.get("name"),
            eb_access_level=eb.get("access_level", "unknown"),
        )

    def _generate_suggestions(self, opp: Opportunity) -> List[str]:
        """生成商機處理建議"""
        suggestions = []

        if not opp.meddic.pain_identified:
            suggestions.append("建議進行 Discovery Call 了解客戶痛點")

        if not opp.contacts:
            suggestions.append("需要補充聯絡人資訊")

        if opp.meddic.champion_score < 5:
            suggestions.append("需要培養內部 Champion")

        if not opp.amount:
            suggestions.append("建議評估專案預算")

        if opp.meddic.total_score < 50:
            suggestions.append(f"MEDDIC 分數偏低 ({opp.meddic.total_score}/100)，需要補足缺口")

        return suggestions

    def _analyze_stage_readiness(self, opp: Opportunity) -> Dict[str, Any]:
        """分析是否可推進到下一階段"""
        from app.pipeline.models import STAGE_ORDER

        current_idx = STAGE_ORDER.index(opp.stage) if opp.stage in STAGE_ORDER else -1

        if current_idx < 0 or current_idx >= len(STAGE_ORDER) - 1:
            return {"can_advance": False, "reason": "已在最終階段"}

        next_stage = STAGE_ORDER[current_idx + 1]
        can_advance, blockers = opp.can_advance_to(next_stage)

        return {
            "current_stage": opp.stage.value,
            "next_stage": next_stage.value,
            "can_advance": can_advance,
            "blockers": blockers,
            "days_in_stage": opp.days_in_stage,
        }

    def _identify_risks(self, opp: Opportunity) -> List[str]:
        """識別風險因素"""
        risks = []

        if opp.is_stale:
            risks.append(f"商機已 {opp.days_since_activity} 天沒有活動")

        if opp.meddic.health in ["weak", "needs_attention"]:
            risks.append(f"MEDDIC 健康度: {opp.meddic.health}")

        if opp.days_in_stage > 30:
            risks.append(f"在 {opp.stage.value} 階段已超過 30 天")

        if not opp.champion:
            risks.append("尚未確認 Champion")

        if not opp.economic_buyer:
            risks.append("尚未確認 Economic Buyer")

        return risks


# 全域實例
_hunter = HunterAgent()


async def process_opportunity(content: str, entities: List[Dict], meddic: Dict = None) -> Dict:
    """便利函數：處理商機"""
    return await _hunter.process_intake(content, entities, meddic)


async def get_suggestion(opp_id: str) -> HunterThinkResult:
    """便利函數：取得建議"""
    return await _hunter.suggest_action(opp_id)
