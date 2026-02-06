"""
Intake Processor

處理 CEO 輸入的核心邏輯
"""

import json
import logging
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

from app.intake.models import (
    CEOInput,
    EnrichedData,
    InputIntent,
    InputStatus,
    InputType,
    ParsedEntity,
    StructuredOpportunity,
)
from app.intake.enricher import DataEnricher

logger = logging.getLogger(__name__)


# 意圖識別的關鍵詞
INTENT_KEYWORDS = {
    InputIntent.OPPORTUNITY: [
        "商機", "客戶", "合作", "有興趣", "潛在", "lead", "prospect",
        "介紹", "認識", "公司", "廠商", "partner", "deal", "案子",
        "需求", "預算", "採購", "想買", "評估",
    ],
    InputIntent.PROJECT: [
        "專案", "開發", "功能", "需求", "實作", "建置", "系統",
        "feature", "project", "做一個", "幫我做", "新增",
    ],
    InputIntent.QUESTION: [
        "？", "?", "什麼", "如何", "為什麼", "怎麼", "是否",
        "有沒有", "能不能", "可以嗎", "嗎",
    ],
    InputIntent.TASK: [
        "幫我", "記得", "提醒", "安排", "預約", "回覆", "處理",
        "todo", "待辦", "追蹤",
    ],
}


class IntakeProcessor:
    """
    CEO 輸入處理器

    負責：
    1. 意圖識別
    2. 實體解析
    3. 資訊補全
    4. 結構化
    5. 路由決策
    """

    def __init__(
        self,
        db_session=None,
        llm_provider=None,
        enricher: Optional[DataEnricher] = None,
        websocket_manager=None,
    ):
        self.db = db_session
        self.llm = llm_provider
        self.enricher = enricher or DataEnricher()
        self.ws = websocket_manager

        self._inputs: Dict[str, CEOInput] = {}

    async def process(
        self,
        content: str,
        input_type: InputType = InputType.TEXT,
        source: str = "web",
        attachments: List[str] = None,
    ) -> CEOInput:
        """
        處理 CEO 輸入

        Args:
            content: 輸入內容
            input_type: 輸入類型
            source: 來源
            attachments: 附件列表

        Returns:
            CEOInput: 處理後的輸入記錄
        """
        # 建立輸入記錄
        input_record = CEOInput(
            id=str(uuid4()),
            raw_content=content,
            input_type=input_type,
            source=source,
            attachments=attachments or [],
            status=InputStatus.PROCESSING,
        )

        self._inputs[input_record.id] = input_record

        try:
            # 1. 意圖識別
            intent, confidence = await self._identify_intent(content)
            input_record.intent = intent
            input_record.intent_confidence = confidence

            logger.info(f"Intent identified: {intent.value} ({confidence:.0%})")

            # 2. 實體解析
            entities = await self._parse_entities(content, intent)
            input_record.parsed_entities = entities

            # 3. 資訊補全（如果是商機）
            if intent == InputIntent.OPPORTUNITY:
                enriched = await self._enrich_opportunity(entities, content)
                input_record.enriched_data = enriched

                # 4. 結構化商機
                opportunity = await self._structure_opportunity(
                    content, entities, enriched
                )
                input_record.structured_opportunity = opportunity
                input_record.structured_data = opportunity.to_lead_data()

            # 5. 生成摘要
            input_record.summary = await self._generate_summary(input_record)
            input_record.suggested_actions = self._suggest_actions(input_record)

            # 6. 決定是否需要確認
            input_record.requires_confirmation = self._needs_confirmation(input_record)

            # 7. 決定路由目標
            input_record.routed_to = self._determine_route(intent)

            # 更新狀態
            input_record.processed_at = datetime.utcnow()

            if input_record.requires_confirmation:
                input_record.status = InputStatus.AWAITING_CONFIRMATION
                await self._request_confirmation(input_record)
            else:
                # 自動執行
                await self._execute_routing(input_record)
                input_record.status = InputStatus.COMPLETED

            # 持久化
            await self._persist_input(input_record)

            return input_record

        except Exception as e:
            logger.error(f"Failed to process input: {e}")
            input_record.status = InputStatus.FAILED
            input_record.error_message = str(e)
            await self._persist_input(input_record)
            raise

    async def confirm(
        self,
        input_id: str,
        confirmed: bool,
        feedback: Optional[str] = None,
        modifications: Optional[Dict[str, Any]] = None,
    ) -> CEOInput:
        """
        CEO 確認輸入解析結果

        Args:
            input_id: 輸入 ID
            confirmed: 是否確認
            feedback: 回饋
            modifications: 修改內容
        """
        input_record = self._inputs.get(input_id)
        if not input_record:
            raise ValueError(f"Input {input_id} not found")

        input_record.ceo_confirmed = confirmed
        input_record.ceo_feedback = feedback
        input_record.ceo_modifications = modifications
        input_record.confirmed_at = datetime.utcnow()

        if confirmed:
            # 應用修改
            if modifications and input_record.structured_opportunity:
                for key, value in modifications.items():
                    if hasattr(input_record.structured_opportunity, key):
                        setattr(input_record.structured_opportunity, key, value)

            # 執行路由
            await self._execute_routing(input_record)
            input_record.status = InputStatus.COMPLETED
            input_record.completed_at = datetime.utcnow()
        else:
            input_record.status = InputStatus.REJECTED

        await self._persist_input(input_record)

        return input_record

    async def get_pending_confirmations(self) -> List[CEOInput]:
        """取得待確認的輸入"""
        return [
            inp for inp in self._inputs.values()
            if inp.status == InputStatus.AWAITING_CONFIRMATION
        ]

    async def get_input(self, input_id: str) -> Optional[CEOInput]:
        """取得輸入記錄"""
        return self._inputs.get(input_id)

    # === 內部方法 ===

    async def _identify_intent(self, content: str) -> Tuple[InputIntent, float]:
        """意圖識別"""
        content_lower = content.lower()

        # 關鍵詞匹配
        scores = {}
        for intent, keywords in INTENT_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in content_lower)
            if score > 0:
                scores[intent] = score

        if not scores:
            return InputIntent.UNKNOWN, 0.0

        # 選擇最高分的意圖
        best_intent = max(scores, key=scores.get)

        # 計算信心度（簡單版本）
        max_score = scores[best_intent]
        confidence = min(0.5 + (max_score * 0.1), 0.95)

        # 如果有 LLM，使用 LLM 進行更精確的識別
        if self.llm:
            intent, confidence = await self._llm_identify_intent(content)

        return best_intent, confidence

    async def _llm_identify_intent(self, content: str) -> Tuple[InputIntent, float]:
        """使用 LLM 識別意圖"""
        prompt = f"""
分析以下 CEO 輸入的意圖：

"{content}"

請判斷這個輸入屬於哪種類型：
1. opportunity - 潛在商機、客戶線索、合作機會
2. project - 專案需求、功能開發
3. question - 問題詢問
4. task - 待辦事項
5. info - 一般資訊分享

回覆 JSON 格式：
{{"intent": "opportunity", "confidence": 0.85, "reasoning": "..."}}
"""
        # TODO: 呼叫 LLM
        return InputIntent.OPPORTUNITY, 0.8

    async def _parse_entities(
        self,
        content: str,
        intent: InputIntent,
    ) -> List[ParsedEntity]:
        """實體解析"""
        entities = []

        # 簡單的正則匹配
        # 公司名稱（中文）
        company_patterns = [
            r'([\u4e00-\u9fff]+(?:公司|企業|集團|科技|股份))',
            r'((?:台灣|美國|日本)?[\u4e00-\u9fff]+(?:銀行|保險|證券))',
        ]
        for pattern in company_patterns:
            matches = re.findall(pattern, content)
            for match in matches:
                entities.append(ParsedEntity(
                    entity_type="company",
                    value=match,
                    confidence=0.7,
                    context=content,
                ))

        # Email
        email_pattern = r'[\w\.-]+@[\w\.-]+\.\w+'
        emails = re.findall(email_pattern, content)
        for email in emails:
            entities.append(ParsedEntity(
                entity_type="email",
                value=email,
                confidence=0.95,
            ))

        # URL
        url_pattern = r'https?://[^\s]+'
        urls = re.findall(url_pattern, content)
        for url in urls:
            entities.append(ParsedEntity(
                entity_type="url",
                value=url,
                confidence=0.95,
            ))

        # 金額
        amount_patterns = [
            r'(\d+(?:,\d{3})*(?:\.\d+)?)\s*(?:萬|億|千|百)?(?:美金|美元|USD|\$)',
            r'\$\s*(\d+(?:,\d{3})*(?:\.\d+)?)',
            r'(\d+(?:,\d{3})*)\s*(?:萬|億)',
        ]
        for pattern in amount_patterns:
            matches = re.findall(pattern, content)
            for match in matches:
                entities.append(ParsedEntity(
                    entity_type="amount",
                    value=match,
                    confidence=0.8,
                ))

        # 人名（簡單版本，實際應用需要 NER）
        # TODO: 使用 LLM 或 NER 模型提取人名

        return entities

    async def _enrich_opportunity(
        self,
        entities: List[ParsedEntity],
        content: str,
    ) -> EnrichedData:
        """補全商機資訊"""
        enriched = EnrichedData()

        # 從 URL 抓取公司資訊
        urls = [e.value for e in entities if e.entity_type == "url"]
        for url in urls:
            if self.enricher:
                company_info = await self.enricher.fetch_url_info(url)
                if company_info:
                    enriched.company_info = company_info
                    enriched.source_urls.append(url)

        # 從公司名稱搜尋資訊
        companies = [e.value for e in entities if e.entity_type == "company"]
        for company in companies:
            if self.enricher:
                info = await self.enricher.search_company(company)
                if info:
                    enriched.company_info = info

        return enriched

    async def _structure_opportunity(
        self,
        content: str,
        entities: List[ParsedEntity],
        enriched: EnrichedData,
    ) -> StructuredOpportunity:
        """結構化商機"""
        # 從實體中提取資訊
        company_name = None
        contact_email = None

        for entity in entities:
            if entity.entity_type == "company" and not company_name:
                company_name = entity.value
            elif entity.entity_type == "email" and not contact_email:
                contact_email = entity.value

        # 從補全資料中獲取更多資訊
        if enriched.company_info:
            company_name = company_name or enriched.company_info.get("name")

        # 判斷緊急程度
        urgency = "normal"
        if any(kw in content for kw in ["急", "盡快", "立刻", "馬上", "urgent"]):
            urgency = "urgent"
        elif any(kw in content for kw in ["重要", "優先", "important"]):
            urgency = "high"

        return StructuredOpportunity(
            company_name=company_name or "未知公司",
            industry=enriched.company_info.get("industry") if enriched.company_info else None,
            contact_email=contact_email,
            urgency=urgency,
            ceo_notes=content,
            source="ceo_referral",
        )

    async def _generate_summary(self, input_record: CEOInput) -> str:
        """生成處理摘要"""
        intent_names = {
            InputIntent.OPPORTUNITY: "商機線索",
            InputIntent.PROJECT: "專案需求",
            InputIntent.QUESTION: "問題詢問",
            InputIntent.TASK: "待辦事項",
            InputIntent.INFO: "資訊記錄",
            InputIntent.UNKNOWN: "未識別",
        }

        summary = f"識別為【{intent_names[input_record.intent]}】"

        if input_record.structured_opportunity:
            opp = input_record.structured_opportunity
            summary += f"\n公司：{opp.company_name}"
            if opp.contact_name:
                summary += f"\n聯絡人：{opp.contact_name}"
            summary += f"\n緊急程度：{opp.urgency}"

        return summary

    def _suggest_actions(self, input_record: CEOInput) -> List[str]:
        """建議後續動作"""
        actions = []

        if input_record.intent == InputIntent.OPPORTUNITY:
            actions.append("建立 Lead 並進入 Sales Pipeline")
            actions.append("由 HUNTER 開始跟進")
            if input_record.structured_opportunity:
                if input_record.structured_opportunity.urgency in ["high", "urgent"]:
                    actions.append("⚠️ 高優先級：建議 24 小時內聯繫")

        elif input_record.intent == InputIntent.PROJECT:
            actions.append("建立專案需求卡片")
            actions.append("由 ORCHESTRATOR 進行需求分析")

        elif input_record.intent == InputIntent.QUESTION:
            actions.append("查詢相關資訊")
            actions.append("整理後回覆 CEO")

        elif input_record.intent == InputIntent.TASK:
            actions.append("建立待辦事項")
            actions.append("設定提醒")

        return actions

    def _needs_confirmation(self, input_record: CEOInput) -> bool:
        """判斷是否需要 CEO 確認"""
        # 信心度低於 80% 需要確認
        if input_record.intent_confidence < 0.8:
            return True

        # 商機類別預設需要確認
        if input_record.intent == InputIntent.OPPORTUNITY:
            return True

        # 未識別需要確認
        if input_record.intent == InputIntent.UNKNOWN:
            return True

        return False

    def _determine_route(self, intent: InputIntent) -> Optional[str]:
        """決定路由目標"""
        routes = {
            InputIntent.OPPORTUNITY: "HUNTER",
            InputIntent.PROJECT: "ORCHESTRATOR",
            InputIntent.QUESTION: None,  # 直接回覆
            InputIntent.TASK: "GATEKEEPER",
            InputIntent.INFO: None,
        }
        return routes.get(intent)

    async def _request_confirmation(self, input_record: CEOInput):
        """請求 CEO 確認"""
        card = input_record.to_confirmation_card()

        # 推送到 WebSocket
        if self.ws:
            await self.ws.broadcast({
                "event": "intake.confirmation_needed",
                "data": card,
            })

        logger.info(f"Confirmation requested for input {input_record.id}")

    async def _execute_routing(self, input_record: CEOInput):
        """執行路由"""
        if input_record.intent == InputIntent.OPPORTUNITY:
            # 建立 Lead
            lead_data = input_record.structured_opportunity.to_lead_data()
            lead_data["source_input_id"] = input_record.id

            # TODO: 呼叫 Lead 建立 API
            lead_id = str(uuid4())  # 模擬

            input_record.created_entity_type = "lead"
            input_record.created_entity_id = lead_id

            logger.info(f"Created lead {lead_id} from input {input_record.id}")

            # 通知 HUNTER
            if self.ws:
                await self.ws.broadcast({
                    "event": "agent.task_assigned",
                    "data": {
                        "agent_id": "HUNTER",
                        "task_type": "new_lead",
                        "lead_id": lead_id,
                        "priority": "high",
                        "source": "ceo_referral",
                    },
                })

    async def _persist_input(self, input_record: CEOInput):
        """持久化輸入記錄"""
        # TODO: 實作資料庫寫入
        pass
