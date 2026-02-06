"""
GATEKEEPER Agent

負責：
- 接收 CEO 輸入
- 識別意圖（opportunity, project, question, task）
- 路由到適當的 Agent 或 Engine
- 初步資料解析和補全
"""

import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from app.engines.meddic.engine import MEDDICEngine


class Intent(Enum):
    """意圖類型"""
    OPPORTUNITY = "opportunity"  # 商機 → HUNTER
    PROJECT = "project"          # 專案 → ORCHESTRATOR
    QUESTION = "question"        # 問題 → 直接回答或知識庫
    TASK = "task"                # 任務 → ORCHESTRATOR
    REPORT = "report"            # 報告 → Dashboard
    CONTROL = "control"          # 控制指令 → 系統


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
    route_to: str  # HUNTER, ORCHESTRATOR, etc.
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

    CEO 輸入的第一關，負責：
    1. 意圖識別
    2. 實體抽取
    3. 路由決策
    4. 觸發相應分析
    """

    # 意圖關鍵詞
    INTENT_KEYWORDS = {
        Intent.OPPORTUNITY: [
            "商機", "客戶", "業務", "銷售", "報價", "提案",
            "介紹", "認識", "公司", "合作", "潛在",
            "lead", "prospect", "deal", "opportunity",
        ],
        Intent.PROJECT: [
            "開發", "建立", "實作", "系統", "功能", "專案",
            "做", "建", "寫", "create", "build", "develop",
        ],
        Intent.QUESTION: [
            "什麼", "為什麼", "如何", "怎麼", "嗎", "？",
            "what", "why", "how", "?",
        ],
        Intent.TASK: [
            "請", "幫我", "處理", "安排", "更新", "修改",
            "please", "help", "update", "fix",
        ],
        Intent.REPORT: [
            "報告", "統計", "數據", "績效", "狀況",
            "report", "stats", "status", "dashboard",
        ],
        Intent.CONTROL: [
            "暫停", "停止", "取消", "重啟", "模式",
            "stop", "pause", "cancel", "mode",
        ],
    }

    # 職稱關鍵詞
    TITLE_KEYWORDS = {
        "c_level": ["CEO", "CTO", "CFO", "COO", "總經理", "執行長", "技術長", "財務長"],
        "vp": ["VP", "副總", "協理", "Vice President"],
        "director": ["Director", "總監", "處長"],
        "manager": ["Manager", "經理", "主管"],
    }

    def __init__(self):
        self.meddic_engine = MEDDICEngine()

    async def analyze(self, content: str, source: str = "ceo") -> IntakeAnalysis:
        """
        分析 CEO 輸入

        Args:
            content: 輸入內容
            source: 來源 (ceo, email, etc.)

        Returns:
            IntakeAnalysis: 分析結果
        """
        # 1. 識別意圖
        intent, intent_confidence = self._detect_intent(content)

        # 2. 抽取實體
        entities = self._extract_entities(content)

        # 3. 決定路由
        route_to = self._determine_route(intent)

        # 4. 生成摘要
        summary = self._generate_summary(content, intent, entities)

        # 5. 如果是商機，進行 MEDDIC 分析
        meddic_analysis = None
        if intent == Intent.OPPORTUNITY:
            meddic = await self.meddic_engine.analyze(content, [e.__dict__ for e in entities])
            meddic_analysis = meddic.to_dict()

        # 6. 建議動作
        suggested_actions = self._suggest_actions(intent, entities, meddic_analysis)

        # 7. 判斷是否需要確認
        requires_confirmation = intent_confidence < 0.8 or intent in [
            Intent.PROJECT, Intent.OPPORTUNITY
        ]

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

    def _detect_intent(self, content: str) -> tuple[Intent, float]:
        """識別意圖"""
        content_lower = content.lower()
        scores = {}

        for intent, keywords in self.INTENT_KEYWORDS.items():
            score = 0
            for keyword in keywords:
                if keyword.lower() in content_lower:
                    score += 1
            scores[intent] = score

        if not any(scores.values()):
            return Intent.TASK, 0.5

        best_intent = max(scores, key=scores.get)
        max_score = scores[best_intent]

        # 計算信心度
        confidence = min(0.95, 0.5 + (max_score * 0.15))

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
            Intent.OPPORTUNITY: "HUNTER",
            Intent.PROJECT: "ORCHESTRATOR",
            Intent.TASK: "ORCHESTRATOR",
            Intent.QUESTION: "KNOWLEDGE",
            Intent.REPORT: "DASHBOARD",
            Intent.CONTROL: "SYSTEM",
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
