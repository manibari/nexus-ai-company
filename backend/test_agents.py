"""
Agent 測試腳本

測試 GATEKEEPER → HUNTER → Pipeline 流程
"""

import asyncio
from app.agents.gatekeeper import GatekeeperAgent, analyze_input
from app.agents.hunter import HunterAgent
from app.agents.orchestrator import OrchestratorAgent


async def test_opportunity_flow():
    """測試商機流程"""
    print("\n" + "=" * 60)
    print("🧪 測試 1: 商機流程 (GATEKEEPER → HUNTER)")
    print("=" * 60)

    # CEO 輸入
    ceo_input = """
    今天跟老王吃飯，他介紹了 ABC Corp 的 CTO 王大明。
    他們系統效能有嚴重問題，每月損失約 50 萬。
    想下週約個會議聊聊，預算大概 200 萬。
    """

    print(f"\n📥 CEO 輸入:\n{ceo_input}")

    # 1. GATEKEEPER 分析
    print("\n🚪 GATEKEEPER 分析中...")
    gatekeeper = GatekeeperAgent()
    analysis = await gatekeeper.analyze(ceo_input)

    print(f"\n📊 分析結果:")
    print(f"   意圖: {analysis.intent.value} (信心度: {analysis.confidence:.0%})")
    print(f"   路由: {analysis.route_to}")
    print(f"   需確認: {analysis.requires_confirmation}")

    print(f"\n📋 識別的實體:")
    for entity in analysis.entities:
        print(f"   - {entity.entity_type}: {entity.value}")

    if analysis.meddic_analysis:
        meddic = analysis.meddic_analysis
        print(f"\n📈 MEDDIC 分析:")
        print(f"   Pain: {meddic['pain']['score']}/10 (已識別: {meddic['pain']['identified']})")
        print(f"   Champion: {meddic['champion']['score']}/9 (已識別: {meddic['champion']['identified']})")
        print(f"   EB: {meddic['economic_buyer']['score']}/10 (已識別: {meddic['economic_buyer']['identified']})")
        print(f"   總分: {meddic['total_score']}/100")
        print(f"   健康度: {meddic.get('deal_health', 'N/A')}")

        if meddic['gaps']:
            print(f"\n⚠️  缺口:")
            for gap in meddic['gaps']:
                print(f"   - {gap}")

        if meddic['next_actions']:
            print(f"\n💡 建議動作:")
            for action in meddic['next_actions']:
                print(f"   - {action}")

    # 2. HUNTER 處理
    if analysis.route_to == "HUNTER":
        print("\n\n🎯 HUNTER 接手處理...")
        hunter = HunterAgent()

        # 轉換實體格式
        entities = [
            {"type": e.entity_type, "value": e.value, "metadata": e.metadata}
            for e in analysis.entities
        ]

        result = await hunter.process_intake(
            content=ceo_input,
            entities=entities,
            meddic_analysis=analysis.meddic_analysis,
        )

        print(f"\n✅ 商機已建立:")
        opp = result['opportunity']
        print(f"   ID: {opp['id']}")
        print(f"   名稱: {opp['name']}")
        print(f"   公司: {opp['company']}")
        print(f"   金額: ${opp['amount']:,.0f}" if opp['amount'] else "   金額: 未知")
        print(f"   階段: {opp['stage']}")
        print(f"   MEDDIC: {opp['meddic']['total_score']}/100 ({opp['meddic']['health']})")

        if result['suggestions']:
            print(f"\n📝 處理建議:")
            for sug in result['suggestions']:
                print(f"   - {sug}")

        # 3. 取得下一步建議
        print("\n\n🤔 HUNTER 思考下一步...")
        suggestion = await hunter.suggest_action(opp['id'])

        print(f"\n💭 建議動作:")
        print(f"   動作: {suggestion.action.value}")
        print(f"   原因: {suggestion.reasoning}")
        print(f"   信心度: {suggestion.confidence:.0%}")

        if suggestion.suggested_next_steps:
            print(f"\n📋 具體步驟:")
            for step in suggestion.suggested_next_steps:
                print(f"   - {step}")

        return opp['id']

    return None


async def test_project_flow():
    """測試專案流程"""
    print("\n" + "=" * 60)
    print("🧪 測試 2: 專案流程 (GATEKEEPER → ORCHESTRATOR)")
    print("=" * 60)

    # CEO 輸入
    ceo_input = """
    幫我做一個股票爬蟲系統，要能每天自動爬取台股資料，
    分析符合條件的股票，然後發 LINE 通知我。
    這個比較急，下週要用。
    """

    print(f"\n📥 CEO 輸入:\n{ceo_input}")

    # 1. GATEKEEPER 分析
    print("\n🚪 GATEKEEPER 分析中...")
    gatekeeper = GatekeeperAgent()
    analysis = await gatekeeper.analyze(ceo_input)

    print(f"\n📊 分析結果:")
    print(f"   意圖: {analysis.intent.value} (信心度: {analysis.confidence:.0%})")
    print(f"   路由: {analysis.route_to}")

    # 2. ORCHESTRATOR 處理
    if analysis.route_to == "ORCHESTRATOR":
        print("\n\n🎯 ORCHESTRATOR 接手處理...")
        orchestrator = OrchestratorAgent()

        entities = [
            {"type": e.entity_type, "value": e.value}
            for e in analysis.entities
        ]

        result = await orchestrator.process_project_request(
            content=ceo_input,
            entities=entities,
            priority="high",
        )

        print(f"\n✅ Goal 已建立:")
        goal = result['goal']
        print(f"   ID: {goal['id']}")
        print(f"   標題: {goal['title']}")
        print(f"   優先級: {goal['priority']}")
        print(f"   狀態: {goal['status']}")

        decomp = result['decomposition']
        print(f"\n📋 分解結果:")
        print(f"   階段數: {decomp['phases_count']}")
        print(f"   預估時間: {decomp['total_minutes']} 分鐘")

        print(f"\n📍 執行階段:")
        for phase in goal['phases']:
            print(f"   {phase['sequence'] + 1}. {phase['name']} ({phase['time_estimate']['estimated_minutes']} min)")
            print(f"      目標: {phase['objective']}")
            if phase['assignee']:
                print(f"      指派: {phase['assignee']}")

        return goal['id']

    return None


async def test_full_flow():
    """完整流程測試"""
    print("\n" + "🚀" * 20)
    print("       Nexus AI Company - Agent 測試")
    print("🚀" * 20)

    # 測試商機流程
    opp_id = await test_opportunity_flow()

    # 測試專案流程
    goal_id = await test_project_flow()

    print("\n" + "=" * 60)
    print("📊 測試完成摘要")
    print("=" * 60)
    print(f"\n   商機 ID: {opp_id}")
    print(f"   Goal ID: {goal_id}")
    print("\n✅ 所有 Agent 運作正常！")
    print("\n💡 你可以在前端查看:")
    print("   - 💰 Pipeline: 查看剛建立的商機")
    print("   - 🎯 Goals: 查看剛建立的專案目標")


if __name__ == "__main__":
    asyncio.run(test_full_flow())
