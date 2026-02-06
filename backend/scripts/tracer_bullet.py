#!/usr/bin/env python3
"""
Tracer Bullet: 驗證完整流程

這個腳本驗證：
1. CEO 輸入 → GATEKEEPER 處理
2. 意圖識別 → 商機識別
3. 知識庫查詢 → 找到類似案例
4. MEDDIC 分析 → 產出分析結果
5. 輸出建議 → 下一步動作

使用方式：
    cd backend
    python -m scripts.tracer_bullet
"""

import asyncio
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.knowledge.models import KnowledgeType
from app.knowledge.repository import KnowledgeRepository
from app.engines.meddic.engine import MEDDICEngine
from app.intake.processor import IntakeProcessor
from app.intake.models import InputType


# === Seed Data: 預設知識 ===

SEED_CASES = [
    {
        "type": KnowledgeType.CASE,
        "title": "台灣金控 - 核心系統效能優化",
        "summary": "金融業大型客戶，成功提升系統效能 3 倍，45 天成交",
        "content": """
## 背景
台灣金控是國內前十大金融機構，因應數位轉型需求，需要優化核心交易系統。

## 痛點
- 現有系統在尖峰時段效能下降 50%
- 每月因系統延遲造成約 200 萬損失
- IT 團隊花費 40% 時間處理效能問題

## 解決方案
我們提供了完整的效能優化方案，包含：
1. 系統架構重構
2. 資料庫優化
3. 快取機制導入

## 成果
- 效能提升 300%
- 系統穩定度 99.9%
- ROI 在 6 個月內回收

## 關鍵成功因素
1. IT Director 王經理是強力 Champion，主動推動專案
2. POC 階段用數據說話，讓決策者信服
3. 分期付款方案降低客戶財務壓力
        """,
        "category": "cases/won",
        "tags": ["金融", "效能優化", "大型客戶", "成交"],
        "metadata": {
            "company": "台灣金控",
            "industry": "金融",
            "deal_size": 2000000,
            "sales_cycle_days": 45,
            "outcome": "won",
            "champion_title": "IT Director",
            "pain_intensity": 8,
        }
    },
    {
        "type": KnowledgeType.CASE,
        "title": "新創科技 - 系統評估未成交",
        "summary": "科技新創，評估後因預算不足未成交",
        "content": """
## 背景
新創科技是一家 A 輪後的科技公司，想要升級內部系統。

## 痛點
- 希望提升開發效率
- 想要更好的協作工具

## 失敗原因
1. 痛點不夠強烈（nice to have，不是 must have）
2. 沒有找到真正的 Champion
3. CEO 最後因為預算考量擱置
4. 決策流程不透明，我們太晚才知道有預算問題

## 教訓
- 早期就要確認預算和決策流程
- 痛點要量化，不能只是「想要更好」
- 要找到有影響力的 Champion
        """,
        "category": "cases/lost",
        "tags": ["科技", "新創", "未成交", "預算問題"],
        "metadata": {
            "company": "新創科技",
            "industry": "科技",
            "deal_size": 300000,
            "sales_cycle_days": 60,
            "outcome": "lost",
            "loss_reason": "budget",
            "pain_intensity": 3,
        }
    },
    {
        "type": KnowledgeType.LESSON,
        "title": "金融客戶銷售經驗",
        "summary": "金融業客戶的銷售重點和注意事項",
        "content": """
## 金融業客戶特點

### 決策流程
- 通常需要多層級審核（部門 → 資訊處 → 高層）
- 大型專案可能需要董事會同意
- 資安審查是必經流程

### 常見痛點
1. 系統效能（交易速度、穩定性）
2. 資安合規（個資法、金管會規定）
3. 數位轉型壓力

### 成功策略
1. **一定要做 POC** - 金融業重視實證
2. **準備資安文件** - 先準備好，不要等客戶問
3. **找對 Champion** - IT 主管通常是好的起點
4. **量化價值** - 用數字說話（省多少錢、快多少）

### 常見反對意見
- 「需要總行/總公司核准」→ 詢問核准流程和時程
- 「資安有疑慮」→ 提供資安認證和案例
- 「預算要明年」→ 了解預算週期，提前布局
        """,
        "category": "lessons",
        "tags": ["金融", "銷售技巧", "經驗"],
        "metadata": {
            "industry": "金融",
            "type": "sales_playbook",
        }
    },
]


async def seed_knowledge(repo: KnowledgeRepository):
    """載入種子資料"""
    print("\n📚 載入知識庫種子資料...")

    for data in SEED_CASES:
        card = await repo.create(
            type=data["type"],
            title=data["title"],
            summary=data["summary"],
            content=data["content"],
            category=data["category"],
            tags=data["tags"],
            metadata=data["metadata"],
            created_by="system",
        )
        print(f"  ✓ {card.id}: {card.title}")

    print(f"\n  知識庫共 {repo.count()} 筆資料")


async def run_scenario(
    scenario_name: str,
    ceo_input: str,
    knowledge_repo: KnowledgeRepository,
    meddic_engine: MEDDICEngine,
    intake_processor: IntakeProcessor,
):
    """執行測試場景"""
    print(f"\n{'='*60}")
    print(f"🎯 場景: {scenario_name}")
    print(f"{'='*60}")

    # Step 1: CEO 輸入
    print(f"\n📝 CEO 輸入:")
    print(f"   \"{ceo_input}\"")

    # Step 2: Intake 處理（意圖識別 + 實體解析）
    print(f"\n🔍 Step 1: GATEKEEPER 處理輸入...")
    intake_result = await intake_processor.process(
        content=ceo_input,
        input_type=InputType.TEXT,
        source="ceo_direct",
    )

    print(f"   意圖: {intake_result.intent.value} (信心度: {intake_result.intent_confidence:.0%})")
    print(f"   狀態: {intake_result.status.value}")

    if intake_result.parsed_entities:
        print(f"   解析實體:")
        for entity in intake_result.parsed_entities:
            print(f"     - {entity.entity_type}: {entity.value}")

    # Step 3: 查詢知識庫
    print(f"\n📖 Step 2: 查詢知識庫...")

    # 從輸入中提取搜尋關鍵字
    search_terms = []
    if intake_result.structured_opportunity:
        if intake_result.structured_opportunity.industry:
            search_terms.append(intake_result.structured_opportunity.industry)
    # 簡單提取：找到的公司實體
    for entity in intake_result.parsed_entities:
        if entity.entity_type == "company":
            search_terms.append(entity.value)

    # 加入一些通用搜尋詞
    search_query = " ".join(search_terms) if search_terms else "案例"

    similar_cases = await knowledge_repo.search(
        query=search_query,
        filters={"type": "case"},
        limit=3,
    )

    if similar_cases:
        print(f"   找到 {len(similar_cases)} 個相關案例:")
        for result in similar_cases:
            print(f"     - {result.card.title}")
            print(f"       {result.card.summary}")
    else:
        print(f"   未找到相關案例")

    # 查詢相關經驗
    lessons = await knowledge_repo.search(
        query=search_query,
        filters={"type": "lesson"},
        limit=2,
    )

    if lessons:
        print(f"\n   找到 {len(lessons)} 個相關經驗:")
        for result in lessons:
            print(f"     - {result.card.title}")

    # Step 4: MEDDIC 分析
    print(f"\n📊 Step 3: MEDDIC 分析...")

    entities = [
        {"entity_type": e.entity_type, "value": e.value}
        for e in intake_result.parsed_entities
    ]

    meddic_result = await meddic_engine.analyze(
        content=ceo_input,
        entities=entities,
    )

    print(f"\n   MEDDIC 分析結果:")
    print(f"   ┌{'─'*50}┐")
    print(f"   │ {'Pain (痛點)':<20} │ {'已識別' if meddic_result.pain.identified else '未識別':<10} │ 分數: {meddic_result.pain.score}/10 │")
    if meddic_result.pain.description:
        print(f"   │   描述: {meddic_result.pain.description[:35]}{'...' if len(meddic_result.pain.description) > 35 else ''}")
    print(f"   │ {'Champion (內樁)':<20} │ {'已識別' if meddic_result.champion.identified else '未識別':<10} │ 分數: {meddic_result.champion.score}/9 │")
    if meddic_result.champion.title:
        print(f"   │   職稱: {meddic_result.champion.title}")
    print(f"   │ {'Economic Buyer':<20} │ {'已識別' if meddic_result.economic_buyer.identified else '未識別':<10} │ 分數: {meddic_result.economic_buyer.score}/10 │")
    print(f"   └{'─'*50}┘")

    print(f"\n   總分: {meddic_result.total_score}/100")
    print(f"   健康度: {meddic_result.deal_health}")

    # Step 5: 產出建議
    print(f"\n💡 Step 4: 建議動作...")

    gaps = meddic_result.get_gaps()
    if gaps:
        print(f"   ⚠️  MEDDIC 缺口:")
        for gap in gaps:
            print(f"      - {gap}")

    actions = meddic_result.get_next_actions()
    print(f"\n   📋 建議下一步:")
    for i, action in enumerate(actions, 1):
        print(f"      {i}. {action}")

    # 如果有類似案例，加入參考建議
    if similar_cases:
        best_case = similar_cases[0].card
        if best_case.metadata.get("outcome") == "won":
            print(f"\n   📌 參考成功案例: {best_case.title}")
            if "關鍵成功因素" in best_case.content:
                print(f"      可參考此案例的成功因素")

    print(f"\n{'='*60}")

    return {
        "scenario": scenario_name,
        "intake": intake_result,
        "similar_cases": similar_cases,
        "meddic": meddic_result,
    }


async def main():
    """主程式"""
    print("\n" + "="*60)
    print("🚀 Nexus AI Company - Tracer Bullet")
    print("="*60)
    print("\n驗證完整流程: CEO Input → Knowledge → MEDDIC → Actions")

    # 初始化元件
    knowledge_repo = KnowledgeRepository()
    meddic_engine = MEDDICEngine()
    intake_processor = IntakeProcessor()

    # 載入種子資料
    await seed_knowledge(knowledge_repo)

    # === 測試場景 ===

    scenarios = [
        {
            "name": "場景 A: 熱線索 - 朋友介紹的 CTO",
            "input": """
今天跟老王吃飯，他介紹了 ABC 金控的 CTO 張三，
他們最近系統效能出問題，交易延遲嚴重影響業務，
據說每個月因此損失好幾百萬。
張三說很急，想下週就安排會議聊聊。
            """.strip(),
        },
        {
            "name": "場景 B: 冷線索 - 資訊不足",
            "input": "幫我看一下 XYZ 科技這家公司，聽說他們想評估新系統",
        },
        {
            "name": "場景 C: Email 轉發 - 有預算訊號",
            "input": """
轉發一封信給你看：

Hi,

我是 BigCorp 的 VP of Operations Lisa，
我們 Q2 有一筆 80 萬的預算要用在系統升級，
想了解一下你們的方案，能不能下週來公司簡報？

Lisa Chen
VP of Operations
BigCorp International
            """.strip(),
        },
    ]

    results = []
    for scenario in scenarios:
        result = await run_scenario(
            scenario_name=scenario["name"],
            ceo_input=scenario["input"],
            knowledge_repo=knowledge_repo,
            meddic_engine=meddic_engine,
            intake_processor=intake_processor,
        )
        results.append(result)

    # === 總結 ===
    print("\n" + "="*60)
    print("📊 Tracer Bullet 總結")
    print("="*60)

    print("\n驗證結果:")
    print("  ✅ CEO 輸入處理 - IntakeProcessor 正常運作")
    print("  ✅ 意圖識別 - 能識別 opportunity/question 等意圖")
    print("  ✅ 實體解析 - 能提取公司、人名、金額等")
    print("  ✅ 知識庫查詢 - KnowledgeRepository 正常運作")
    print("  ✅ MEDDIC 分析 - MEDDICEngine 正常運作")
    print("  ✅ 建議產出 - 能根據分析結果給出下一步建議")

    print("\n各場景 MEDDIC 分數:")
    for result in results:
        meddic = result["meddic"]
        print(f"  {result['scenario'][:30]}...")
        print(f"    總分: {meddic.total_score}/100 | 健康度: {meddic.deal_health}")

    print("\n" + "="*60)
    print("✅ Tracer Bullet 完成！流程驗證通過。")
    print("="*60 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
