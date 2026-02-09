"""
GATEKEEPER Agent

負責：
- 接收 CEO 輸入
- 使用 Gemini 識別意圖
- 路由到適當的 Agent
- 實體解析和補全

意圖類型：
- product_feature: 產品功能需求 → PM
- product_bug: 產品 Bug → QA
- opportunity: 商機 → SALES
- project_status: 專案狀態 → ORCHESTRATOR
- task: 任務 → ORCHESTRATOR
- question: 問題 → 直接回答
"""

import json
import logging
import os
import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from app.engines.meddic.engine import MEDDICEngine
from app.agents.activity_log import ActivityType, get_activity_repo

logger = logging.getLogger(__name__)


class Intent(Enum):
    """意圖類型"""
    PRODUCT_FEATURE = "product_feature"  # 產品功能需求 → PM
    PRODUCT_BUG = "product_bug"          # 產品 Bug → QA
    OPPORTUNITY = "opportunity"          # 商機 → SALES
    PROJECT_STATUS = "project_status"    # 專案狀態 → ORCHESTRATOR
    PROJECT = "project"                  # 新專案 → ORCHESTRATOR
    QUESTION = "question"                # 問題 → 直接回答或知識庫
    TASK = "task"                        # 任務 → ORCHESTRATOR
    REPORT = "report"                    # 報告 → Dashboard
    CONTROL = "control"                  # 控制指令 → 系統
    INFO = "info"                        # 資訊分享 → 記錄


@dataclass
class ParsedEntity:
    """解析出的實體"""
    entity_type: str  # person, company, date, amount, etc.
    value: str
    confidence: float = 0.8
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class IntakeAnalysis:
    """輸入分析結果"""
    intent: Intent
    confidence: float
    entities: List[ParsedEntity]
    summary: str
    suggested_actions: List[str]
    route_to: str  # SALES, ORCHESTRATOR, etc.
    requires_confirmation: bool = True
    meddic_analysis: Optional[Dict] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "intent": self.intent.value,
            "confidence": self.confidence,
            "entities": [
                {
                    "type": e.entity_type,
                    "value": e.value,
                    "confidence": e.confidence,
                }
                for e in self.entities
            ],
            "summary": self.summary,
            "suggested_actions": self.suggested_actions,
            "route_to": self.route_to,
            "requires_confirmation": self.requires_confirmation,
            "meddic": self.meddic_analysis,
        }


class GatekeeperAgent:
    """
    GATEKEEPER Agent

    CEO 輸入的第一關，使用 Gemini 進行：
    1. 意圖識別
    2. 實體抽取
    3. 路由決策
    4. 觸發相應分析
    """

    # 已知專案/產品（用於 Gemini prompt）
    KNOWN_PROJECTS = {
        "StockPulse": "美股分析軟體，提供股票報價、技術指標、AI 分析等功能",
        "Nexus AI Company": "本公司的 AI Agent 系統",
    }

    # 職稱關鍵詞（用於實體抽取）
    TITLE_KEYWORDS = {
        "c_level": ["CEO", "CTO", "CFO", "COO", "總經理", "執行長", "技術長", "財務長"],
        "vp": ["VP", "副總", "協理", "Vice President"],
        "director": ["Director", "總監", "處長"],
        "manager": ["Manager", "經理", "主管"],
    }

    def __init__(self):
        self.meddic_engine = MEDDICEngine()
        self._gemini_client = None

    @property
    def agent_id(self) -> str:
        return "GATEKEEPER"

    @property
    def agent_name(self) -> str:
        return "Gatekeeper Agent"

    async def handle(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """AgentHandler 介面實作"""
        content = payload.get("content", "")
        source = payload.get("source", "ceo")
        analysis = await self.analyze(content, source)
        return analysis.to_dict()

    def _get_gemini(self):
        """延遲初始化 Gemini client"""
        if self._gemini_client is None:
            import google.generativeai as genai
            api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
            if not api_key:
                logger.warning("No Gemini API key found, falling back to keyword matching")
                return None
            genai.configure(api_key=api_key)
            self._gemini_client = genai.GenerativeModel("gemini-2.5-flash")
        return self._gemini_client

    async def analyze(self, content: str, source: str = "ceo") -> IntakeAnalysis:
        """
        分析 CEO 輸入

        Args:
            content: 輸入內容
            source: 來源 (ceo, email, etc.)

        Returns:
            IntakeAnalysis: 分析結果
        """
        # 記錄活動開始
        activity_repo = get_activity_repo()
        await activity_repo.log(
            agent_id="GATEKEEPER",
            agent_name="Gatekeeper Agent",
            activity_type=ActivityType.TASK_START,
            message=f"分析 CEO 指令: {content[:50]}...",
            metadata={"source": source, "content_preview": content[:100]},
        )

        # 1. 使用 Gemini 識別意圖和實體
        gemini_result = await self._analyze_with_gemini(content)

        if gemini_result:
            intent = gemini_result["intent"]
            intent_confidence = gemini_result["confidence"]
            entities = gemini_result["entities"]
            route_to = gemini_result["next_agent"]
            summary = gemini_result["summary"]
            suggested_actions = gemini_result["suggested_actions"]
        else:
            # Fallback: 使用關鍵字匹配
            intent, intent_confidence = self._detect_intent_fallback(content)
            entities = self._extract_entities(content)
            route_to = self._determine_route(intent)
            summary = self._generate_summary(content, intent, entities)
            suggested_actions = self._suggest_actions(intent, entities, None)

        # 2. 如果是商機，進行 MEDDIC 分析
        meddic_analysis = None
        if intent == Intent.OPPORTUNITY:
            meddic = await self.meddic_engine.analyze(content, [e.__dict__ for e in entities])
            meddic_analysis = meddic.to_dict()

        # 3. 判斷是否需要確認
        requires_confirmation = intent_confidence < 0.9 or intent in [
            Intent.PROJECT, Intent.OPPORTUNITY, Intent.PRODUCT_FEATURE
        ]

        # 記錄活動完成
        await activity_repo.log(
            agent_id="GATEKEEPER",
            agent_name="Gatekeeper Agent",
            activity_type=ActivityType.TASK_END,
            message=f"分析完成: {intent.value} → {route_to}",
            metadata={
                "intent": intent.value,
                "confidence": intent_confidence,
                "route_to": route_to,
            },
        )

        return IntakeAnalysis(
            intent=intent,
            confidence=intent_confidence,
            entities=entities,
            summary=summary,
            suggested_actions=suggested_actions,
            route_to=route_to,
            requires_confirmation=requires_confirmation,
            meddic_analysis=meddic_analysis,
        )

    async def _analyze_with_gemini(self, content: str) -> Optional[Dict[str, Any]]:
        """使用 Gemini 分析意圖和實體"""
        gemini = self._get_gemini()
        if not gemini:
            return None

        # 構建 prompt
        projects_info = "\n".join([
            f"- {name}: {desc}" for name, desc in self.KNOWN_PROJECTS.items()
        ])

        prompt = f"""你是 Nexus AI Company 的 GATEKEEPER Agent。分析 CEO 指令，判斷意圖並提取實體。

## 意圖類型（必須選擇其一）
- product_feature: 產品功能需求（新增/修改/優化現有產品功能）
- product_bug: 產品 Bug 回報（功能故障、錯誤）
- opportunity: 商機/銷售線索（客戶、合作、業務機會）
- project_status: 專案狀態查詢（進度、狀況）
- project: 全新專案需求
- task: 直接任務指派
- question: 一般問題
- info: 資訊分享/記錄

## 已知專案/產品
{projects_info}

## CEO 指令
{content}

## 回應格式（純 JSON，不要 markdown）
{{
  "intent": "product_feature",
  "confidence": 0.95,
  "project_name": "StockPulse",
  "feature_description": "...",
  "summary": "StockPulse 功能需求：...",
  "next_agent": "PM",
  "suggested_actions": ["由 PM 設計功能規格", "建立 Feature Request"],
  "reasoning": "..."
}}

重要：
1. 如果提到現有產品的功能改進，一定是 product_feature，不是 opportunity
2. 如果提到「股票軟體」「StockPulse」等，這是我們的產品，不是商機
3. next_agent 對應：product_feature→PM, product_bug→QA, opportunity→SALES, project_status→ORCHESTRATOR
"""

        try:
            response = gemini.generate_content(prompt)
            text = response.text.strip()

            # 清理可能的 markdown 標記
            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
            text = text.strip()

            result = json.loads(text)

            # 轉換 intent 字串為 Enum
            intent_str = result.get("intent", "task")
            try:
                intent = Intent(intent_str)
            except ValueError:
                intent = Intent.TASK

            # 構建 entities
            entities = []
            if result.get("project_name"):
                entities.append(ParsedEntity(
                    entity_type="project",
                    value=result["project_name"],
                    confidence=result.get("confidence", 0.8),
                ))
            if result.get("feature_description"):
                entities.append(ParsedEntity(
                    entity_type="feature",
                    value=result["feature_description"],
                    confidence=result.get("confidence", 0.8),
                ))
            if result.get("company_name"):
                entities.append(ParsedEntity(
                    entity_type="company",
                    value=result["company_name"],
                    confidence=result.get("confidence", 0.8),
                ))

            return {
                "intent": intent,
                "confidence": result.get("confidence", 0.8),
                "entities": entities,
                "summary": result.get("summary", ""),
                "next_agent": result.get("next_agent", "ORCHESTRATOR"),
                "suggested_actions": result.get("suggested_actions", []),
                "reasoning": result.get("reasoning", ""),
            }

        except Exception as e:
            logger.error(f"Gemini analysis failed: {e}")
            return None

    def _detect_intent_fallback(self, content: str) -> tuple[Intent, float]:
        """識別意圖 (Fallback: 關鍵字匹配)"""
        content_lower = content.lower()

        # 關鍵字映射
        intent_keywords = {
            Intent.PRODUCT_FEATURE: [
                "功能", "新增", "加入", "優化", "改進", "要能", "需要", "希望",
                "stockpulse", "股票軟體", "大盤", "feature",
            ],
            Intent.PRODUCT_BUG: [
                "壞了", "錯誤", "bug", "故障", "不能用", "問題",
            ],
            Intent.OPPORTUNITY: [
                "商機", "客戶", "業務", "銷售", "報價", "提案",
                "介紹", "認識", "合作", "潛在", "想買",
            ],
            Intent.PROJECT_STATUS: [
                "進度", "狀態", "如何", "怎樣了",
            ],
            Intent.PROJECT: [
                "開發", "建立", "新專案", "create", "build",
            ],
            Intent.QUESTION: [
                "什麼", "為什麼", "如何", "怎麼", "嗎", "？",
            ],
            Intent.TASK: [
                "請", "幫我", "處理", "安排",
            ],
        }

        scores = {}
        for intent, keywords in intent_keywords.items():
            score = sum(1 for kw in keywords if kw.lower() in content_lower)
            scores[intent] = score

        if not any(scores.values()):
            return Intent.TASK, 0.5

        best_intent = max(scores, key=scores.get)
        max_score = scores[best_intent]
        confidence = min(0.85, 0.5 + (max_score * 0.15))

        return best_intent, confidence

    def _extract_entities(self, content: str) -> List[ParsedEntity]:
        """抽取實體"""
        entities = []

        # 抽取公司名稱 (簡單規則：X公司, X Corp, X Ltd 等)
        company_patterns = [
            r'([A-Z][A-Za-z]+\s*(Corp|Corporation|Ltd|Inc|公司|企業|集團))',
            r'([A-Z]{2,}\s*(Corp|Corporation|Ltd|Inc|公司|企業))',
        ]
        for pattern in company_patterns:
            matches = re.findall(pattern, content)
            for match in matches:
                company_name = match[0] if isinstance(match, tuple) else match
                entities.append(ParsedEntity(
                    entity_type="company",
                    value=company_name,
                    confidence=0.8,
                ))

        # 抽取人名和職稱
        for level, titles in self.TITLE_KEYWORDS.items():
            for title in titles:
                if title in content:
                    # 嘗試找到名字（職稱前後的中文名或英文名）
                    pattern = rf'([A-Z][a-z]+|[\u4e00-\u9fff]{{2,3}})\s*{title}|{title}\s*([A-Z][a-z]+|[\u4e00-\u9fff]{{2,3}})'
                    matches = re.findall(pattern, content)
                    for match in matches:
                        name = match[0] or match[1]
                        if name:
                            entities.append(ParsedEntity(
                                entity_type="person",
                                value=name,
                                confidence=0.7,
                                metadata={"title": title, "level": level},
                            ))

        # 抽取金額
        amount_patterns = [
            r'(\d+(?:,\d{3})*(?:\.\d+)?)\s*(萬|億|K|M|million|百萬)?',
        ]
        for pattern in amount_patterns:
            matches = re.findall(pattern, content)
            for match in matches:
                if match[0]:
                    value = float(match[0].replace(',', ''))
                    unit = match[1] if len(match) > 1 else ''

                    # 單位轉換
                    if unit in ['萬', 'K']:
                        value *= 10000
                    elif unit in ['億', 'M', 'million', '百萬']:
                        value *= 100000000 if unit == '億' else 1000000

                    if value > 1000:  # 過濾掉小數字
                        entities.append(ParsedEntity(
                            entity_type="amount",
                            value=str(int(value)),
                            confidence=0.6,
                            metadata={"original": match[0] + (match[1] or '')},
                        ))

        # 抽取日期
        date_patterns = [
            r'(下週|下周|明天|今天|這週|這周|本週|本周)',
            r'(\d{1,2}[/\-]\d{1,2})',
            r'(\d{1,2}月\d{1,2}[日號])',
        ]
        for pattern in date_patterns:
            matches = re.findall(pattern, content)
            for match in matches:
                entities.append(ParsedEntity(
                    entity_type="date",
                    value=match,
                    confidence=0.7,
                ))

        return entities

    def _determine_route(self, intent: Intent) -> str:
        """決定路由目標"""
        routes = {
            Intent.PRODUCT_FEATURE: "PM",
            Intent.PRODUCT_BUG: "QA",
            Intent.OPPORTUNITY: "SALES",
            Intent.PROJECT_STATUS: "ORCHESTRATOR",
            Intent.PROJECT: "ORCHESTRATOR",
            Intent.TASK: "ORCHESTRATOR",
            Intent.QUESTION: "KNOWLEDGE",
            Intent.REPORT: "DASHBOARD",
            Intent.CONTROL: "SYSTEM",
            Intent.INFO: "KNOWLEDGE",
        }
        return routes.get(intent, "ORCHESTRATOR")

    def _generate_summary(
        self,
        content: str,
        intent: Intent,
        entities: List[ParsedEntity]
    ) -> str:
        """生成摘要"""
        parts = []

        # 意圖描述
        intent_desc = {
            Intent.OPPORTUNITY: "這是一個商機",
            Intent.PROJECT: "這是一個專案需求",
            Intent.QUESTION: "這是一個問題",
            Intent.TASK: "這是一個任務",
            Intent.REPORT: "這是一個報告請求",
            Intent.CONTROL: "這是一個控制指令",
        }
        parts.append(intent_desc.get(intent, "待處理項目"))

        # 關鍵實體
        companies = [e.value for e in entities if e.entity_type == "company"]
        people = [e.value for e in entities if e.entity_type == "person"]
        amounts = [e.value for e in entities if e.entity_type == "amount"]

        if companies:
            parts.append(f"公司: {', '.join(companies)}")
        if people:
            parts.append(f"聯絡人: {', '.join(people)}")
        if amounts:
            parts.append(f"金額: {', '.join(amounts)}")

        return "\n".join(parts)

    def _suggest_actions(
        self,
        intent: Intent,
        entities: List[ParsedEntity],
        meddic: Optional[Dict]
    ) -> List[str]:
        """建議動作"""
        actions = []

        if intent == Intent.OPPORTUNITY:
            actions.append("建立商機記錄")

            # 檢查 MEDDIC 分析
            if meddic:
                if not meddic.get("champion", {}).get("identified"):
                    actions.append("確認內部支持者 (Champion)")
                if not meddic.get("economic_buyer", {}).get("identified"):
                    actions.append("確認經濟決策者 (EB)")
                if meddic.get("gaps"):
                    actions.extend([f"補足: {gap}" for gap in meddic["gaps"][:2]])

            # 檢查實體
            has_company = any(e.entity_type == "company" for e in entities)
            has_contact = any(e.entity_type == "person" for e in entities)

            if not has_company:
                actions.append("補充公司名稱")
            if not has_contact:
                actions.append("補充聯絡人資訊")

        elif intent == Intent.PROJECT:
            actions.append("建立專案目標 (Goal)")
            actions.append("分解執行階段 (Phases)")
            actions.append("指派執行者")

        elif intent == Intent.TASK:
            actions.append("建立任務")
            actions.append("指派負責人")

        elif intent == Intent.QUESTION:
            actions.append("查詢知識庫")
            actions.append("生成回答")

        return actions[:5]  # 最多 5 個建議


# 全域實例
_gatekeeper = GatekeeperAgent()


async def analyze_input(content: str, source: str = "ceo") -> IntakeAnalysis:
    """便利函數：分析輸入"""
    return await _gatekeeper.analyze(content, source)
