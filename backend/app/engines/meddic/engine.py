"""
MEDDIC Analysis Engine

銷售機會分析引擎（Tracer Bullet 版本）
"""

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class PainLevel(Enum):
    """痛點強度"""
    NONE = 0
    LOW = 3
    MEDIUM = 5
    HIGH = 7
    CRITICAL = 9


class ChampionStrength(Enum):
    """Champion 強度"""
    NONE = "none"
    WEAK = "weak"
    MEDIUM = "medium"
    STRONG = "strong"


class EBAccessLevel(Enum):
    """Economic Buyer 接觸層級"""
    UNKNOWN = "unknown"
    IDENTIFIED = "identified"
    CONTACTED = "contacted"
    MEETING = "meeting"
    COMMITTED = "committed"


@dataclass
class PainAnalysis:
    """痛點分析"""
    identified: bool = False
    description: Optional[str] = None
    intensity: int = 0  # 0-10
    is_quantified: bool = False
    business_impact: Optional[str] = None
    urgency_signals: List[str] = field(default_factory=list)

    @property
    def score(self) -> int:
        return self.intensity


@dataclass
class ChampionAnalysis:
    """Champion 分析"""
    identified: bool = False
    name: Optional[str] = None
    title: Optional[str] = None
    strength: ChampionStrength = ChampionStrength.NONE
    influence_signals: List[str] = field(default_factory=list)
    engagement_signals: List[str] = field(default_factory=list)

    @property
    def score(self) -> int:
        scores = {
            ChampionStrength.NONE: 0,
            ChampionStrength.WEAK: 3,
            ChampionStrength.MEDIUM: 6,
            ChampionStrength.STRONG: 9,
        }
        return scores[self.strength]


@dataclass
class EconomicBuyerAnalysis:
    """Economic Buyer 分析"""
    identified: bool = False
    name: Optional[str] = None
    title: Optional[str] = None
    access_level: EBAccessLevel = EBAccessLevel.UNKNOWN
    has_budget_authority: Optional[bool] = None
    expressed_support: bool = False

    @property
    def score(self) -> int:
        scores = {
            EBAccessLevel.UNKNOWN: 0,
            EBAccessLevel.IDENTIFIED: 2,
            EBAccessLevel.CONTACTED: 4,
            EBAccessLevel.MEETING: 7,
            EBAccessLevel.COMMITTED: 10,
        }
        return scores[self.access_level]


@dataclass
class MEDDICAnalysis:
    """完整 MEDDIC 分析結果"""
    pain: PainAnalysis = field(default_factory=PainAnalysis)
    champion: ChampionAnalysis = field(default_factory=ChampionAnalysis)
    economic_buyer: EconomicBuyerAnalysis = field(default_factory=EconomicBuyerAnalysis)

    # 簡化版：暫不實作這三個
    metrics: Optional[Dict] = None
    decision_criteria: Optional[Dict] = None
    decision_process: Optional[Dict] = None

    @property
    def total_score(self) -> int:
        """總分（0-100）"""
        # Pain: 30%, Champion: 35%, EB: 35%
        pain_score = self.pain.score * 3  # max 30
        champion_score = int(self.champion.score * 3.5)  # max ~31
        eb_score = int(self.economic_buyer.score * 3.5)  # max 35
        return pain_score + champion_score + eb_score

    @property
    def deal_health(self) -> str:
        """Deal 健康度"""
        score = self.total_score
        if score >= 70:
            return "healthy"
        elif score >= 50:
            return "at_risk"
        elif score >= 30:
            return "needs_attention"
        else:
            return "weak"

    def get_gaps(self) -> List[str]:
        """找出 MEDDIC 缺口"""
        gaps = []
        if not self.pain.identified:
            gaps.append("痛點未確認")
        elif self.pain.intensity < 6:
            gaps.append("痛點強度不足")
        if not self.champion.identified:
            gaps.append("尚未找到 Champion")
        elif self.champion.strength in [ChampionStrength.NONE, ChampionStrength.WEAK]:
            gaps.append("Champion 影響力不足")
        if not self.economic_buyer.identified:
            gaps.append("Economic Buyer 未確認")
        elif self.economic_buyer.access_level in [EBAccessLevel.UNKNOWN, EBAccessLevel.IDENTIFIED]:
            gaps.append("尚未接觸到 Economic Buyer")
        return gaps

    def get_next_actions(self) -> List[str]:
        """建議下一步動作"""
        actions = []
        gaps = self.get_gaps()

        if "痛點未確認" in gaps:
            actions.append("進行 Discovery Call，深入了解客戶痛點")
        if "痛點強度不足" in gaps:
            actions.append("量化痛點的商業影響（成本、時間、風險）")
        if "尚未找到 Champion" in gaps:
            actions.append("識別並培養內部支持者")
        if "Champion 影響力不足" in gaps:
            actions.append("評估 Champion 是否有足夠影響力，或尋找更高層級支持者")
        if "Economic Buyer 未確認" in gaps:
            actions.append("向 Champion 確認決策者是誰")
        if "尚未接觸到 Economic Buyer" in gaps:
            actions.append("透過 Champion 安排與決策者的會議")

        if not actions:
            actions.append("持續推進，準備提案")

        return actions

    def to_dict(self) -> Dict[str, Any]:
        return {
            "pain": {
                "identified": self.pain.identified,
                "description": self.pain.description,
                "intensity": self.pain.intensity,
                "score": self.pain.score,
            },
            "champion": {
                "identified": self.champion.identified,
                "name": self.champion.name,
                "title": self.champion.title,
                "strength": self.champion.strength.value,
                "score": self.champion.score,
            },
            "economic_buyer": {
                "identified": self.economic_buyer.identified,
                "name": self.economic_buyer.name,
                "title": self.economic_buyer.title,
                "access_level": self.economic_buyer.access_level.value,
                "score": self.economic_buyer.score,
            },
            "total_score": self.total_score,
            "deal_health": self.deal_health,
            "gaps": self.get_gaps(),
            "next_actions": self.get_next_actions(),
        }


class MEDDICEngine:
    """
    MEDDIC 分析引擎

    分析商機的 MEDDIC 指標：
    - Metrics (指標)
    - Economic Buyer (經濟決策者)
    - Decision Criteria (決策標準)
    - Decision Process (決策流程)
    - Identify Pain (識別痛點)
    - Champion (內部支持者)
    """

    # 痛點關鍵詞
    PAIN_KEYWORDS = {
        "high": ["急", "緊急", "馬上", "立刻", "嚴重", "損失", "無法", "停擺"],
        "medium": ["問題", "困擾", "影響", "效能", "效率", "太慢", "不足"],
        "low": ["想要", "希望", "評估", "了解", "比較"],
    }

    # 職稱關鍵詞
    TITLE_KEYWORDS = {
        "c_level": ["CEO", "CTO", "CFO", "COO", "總經理", "執行長", "技術長"],
        "vp": ["VP", "副總", "協理"],
        "director": ["Director", "總監", "處長"],
        "manager": ["Manager", "經理", "主管"],
    }

    def __init__(self):
        pass

    async def analyze(
        self,
        content: str,
        entities: List[Dict] = None,
        context: Dict = None,
    ) -> MEDDICAnalysis:
        """
        分析內容的 MEDDIC 指標

        Args:
            content: 原始內容（CEO 輸入、Email 等）
            entities: 已解析的實體（公司、人名等）
            context: 額外上下文

        Returns:
            MEDDICAnalysis 分析結果
        """
        entities = entities or []
        context = context or {}

        analysis = MEDDICAnalysis()

        # 1. 分析痛點
        analysis.pain = self._analyze_pain(content)

        # 2. 分析 Champion
        analysis.champion = self._analyze_champion(content, entities)

        # 3. 分析 Economic Buyer
        analysis.economic_buyer = self._analyze_economic_buyer(content, entities)

        return analysis

    def _analyze_pain(self, content: str) -> PainAnalysis:
        """分析痛點"""
        pain = PainAnalysis()
        content_lower = content.lower()

        # 檢測痛點關鍵詞
        urgency_signals = []
        intensity = 0

        for keyword in self.PAIN_KEYWORDS["high"]:
            if keyword in content:
                urgency_signals.append(keyword)
                intensity = max(intensity, 8)

        for keyword in self.PAIN_KEYWORDS["medium"]:
            if keyword in content:
                urgency_signals.append(keyword)
                intensity = max(intensity, 5)

        for keyword in self.PAIN_KEYWORDS["low"]:
            if keyword in content:
                if intensity == 0:
                    intensity = 3

        if urgency_signals:
            pain.identified = True
            pain.intensity = intensity
            pain.urgency_signals = urgency_signals

            # 嘗試提取痛點描述
            # 找包含痛點關鍵詞的句子
            sentences = re.split(r'[。！？\n]', content)
            for sentence in sentences:
                if any(kw in sentence for kw in urgency_signals):
                    pain.description = sentence.strip()
                    break

        # 檢測是否量化
        if re.search(r'\d+\s*[%萬億元美金]', content):
            pain.is_quantified = True
            pain.intensity = min(pain.intensity + 1, 10)

        return pain

    def _analyze_champion(
        self,
        content: str,
        entities: List[Dict]
    ) -> ChampionAnalysis:
        """分析 Champion"""
        champion = ChampionAnalysis()

        # 從實體中找人名和職稱
        for entity in entities:
            if entity.get("entity_type") == "person":
                champion.identified = True
                champion.name = entity.get("value")

        # 檢測職稱
        for level, titles in self.TITLE_KEYWORDS.items():
            for title in titles:
                if title in content:
                    champion.identified = True
                    champion.title = title

                    # 根據職稱判斷強度
                    if level == "c_level":
                        champion.strength = ChampionStrength.STRONG
                    elif level in ["vp", "director"]:
                        champion.strength = ChampionStrength.MEDIUM
                    else:
                        champion.strength = ChampionStrength.WEAK
                    break

        # 檢測主動性信號
        active_signals = ["主動", "聯繫", "約", "安排", "介紹", "推薦"]
        for signal in active_signals:
            if signal in content:
                champion.engagement_signals.append(signal)
                # 有主動信號，提升強度
                if champion.strength == ChampionStrength.WEAK:
                    champion.strength = ChampionStrength.MEDIUM
                elif champion.strength == ChampionStrength.MEDIUM:
                    champion.strength = ChampionStrength.STRONG

        return champion

    def _analyze_economic_buyer(
        self,
        content: str,
        entities: List[Dict]
    ) -> EconomicBuyerAnalysis:
        """分析 Economic Buyer"""
        eb = EconomicBuyerAnalysis()

        # 檢測 C-level 或決策者關鍵詞
        eb_keywords = ["CEO", "總經理", "老闆", "決策", "拍板", "簽約", "預算"]

        for keyword in eb_keywords:
            if keyword in content:
                eb.identified = True
                break

        # 檢測預算相關
        if re.search(r'預算|budget|\d+\s*萬', content, re.IGNORECASE):
            eb.has_budget_authority = True
            eb.access_level = EBAccessLevel.IDENTIFIED

        # 檢測會議相關
        if re.search(r'會議|見面|meeting|約|安排', content, re.IGNORECASE):
            if eb.identified:
                eb.access_level = EBAccessLevel.MEETING

        return eb

    async def analyze_with_history(
        self,
        content: str,
        previous_analysis: Optional[MEDDICAnalysis] = None,
        activities: List[Dict] = None,
    ) -> MEDDICAnalysis:
        """
        結合歷史資料分析

        用於已有互動記錄的 Deal
        """
        # 先做基本分析
        analysis = await self.analyze(content)

        # 如果有之前的分析，合併（取較高值）
        if previous_analysis:
            if previous_analysis.pain.intensity > analysis.pain.intensity:
                analysis.pain = previous_analysis.pain
            if previous_analysis.champion.score > analysis.champion.score:
                analysis.champion = previous_analysis.champion
            if previous_analysis.economic_buyer.score > analysis.economic_buyer.score:
                analysis.economic_buyer = previous_analysis.economic_buyer

        return analysis
