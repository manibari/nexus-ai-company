"""
Sales Agent

AgentHandler implementation for sales pipeline management.

Routes by action:
- default/intake: extract entities → validate → create client + deal → log activity
- advance_stage: state machine transition
- daily_briefing: stagnation alerts + pipeline summary
- generate_quote: cost-plus pricing (Phase 1)

Uses Gemini 2.5 Flash for entity extraction and sales strategy.
"""

import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

from app.agents.activity_log import ActivityType, get_activity_repo
from app.sales.csv_repository import get_sales_repo
from app.sales.models import (
    ActivityTypeEnum,
    Client,
    Deal,
    DealStage,
    Quote,
    SalesActivity,
)
from app.sales.pipeline_state_machine import (
    advance_deal,
    close_lost,
    close_won,
    detect_stagnant_deals,
    validate_new_deal,
)

logger = logging.getLogger(__name__)

# CEO escalation thresholds
CEO_ESCALATION_AMOUNT = 3_000_000  # $3M
CEO_ESCALATION_STAGNATION_DAYS = 10


class SalesAgent:
    """
    Sales Agent - handles sales pipeline operations.

    Implements AgentHandler protocol (agent_id, agent_name, handle).
    """

    def __init__(self):
        self._gemini_client = None

    @property
    def agent_id(self) -> str:
        return "SALES"

    @property
    def agent_name(self) -> str:
        return "Sales Agent"

    def _get_gemini(self):
        """Lazy-init Gemini client."""
        if self._gemini_client is None:
            import google.generativeai as genai
            api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
            if not api_key:
                logger.warning("No Gemini API key found")
                return None
            genai.configure(api_key=api_key)
            self._gemini_client = genai.GenerativeModel("gemini-2.5-flash")
        return self._gemini_client

    async def handle(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        AgentHandler interface.

        Routing by 'action' field:
        - (missing/intake): process new opportunity from GATEKEEPER
        - advance_stage: advance deal to next stage
        - daily_briefing: pipeline health report
        - generate_quote: generate cost-plus quote
        """
        action = payload.get("action", "intake")

        if action == "advance_stage":
            return await self._handle_advance_stage(payload)
        elif action == "daily_briefing":
            return await self._handle_daily_briefing()
        elif action == "generate_quote":
            return await self._handle_generate_quote(payload)
        else:
            return await self._handle_intake(payload)

    # === Intake: new opportunity ===

    async def _handle_intake(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Process new opportunity from GATEKEEPER dispatch."""
        activity_repo = get_activity_repo()
        repo = get_sales_repo()

        content = payload.get("content", "")
        raw_entities = payload.get("entities", [])

        # Normalise entity format (GATEKEEPER uses entity_type, HUNTER uses type)
        entities = [
            {
                "type": e.get("entity_type", e.get("type")),
                "value": e.get("value"),
                "metadata": e.get("metadata", {}),
            }
            for e in raw_entities
        ]

        await activity_repo.log(
            agent_id="SALES",
            agent_name="Sales Agent",
            activity_type=ActivityType.TASK_START,
            message=f"處理商機: {content[:60]}",
        )

        # 1. Extract structured fields via Gemini (or fallback to entities)
        extracted = await self._extract_deal_info(content, entities)
        client_name = extracted.get("client_name", "")
        amount = extracted.get("amount", 0)
        next_action = extracted.get("next_action", "")
        title = extracted.get("title", f"{client_name} 商機" if client_name else "新商機")
        industry = extracted.get("industry", "")

        # 2. Validate
        missing = validate_new_deal(client_name, amount, next_action)
        if missing:
            # Still create with defaults rather than reject entirely
            if "client_name" in missing and not client_name:
                client_name = "Unknown"
            if "amount" in missing and (amount is None or amount <= 0):
                amount = 0
            if "next_action" in missing and not next_action:
                next_action = "待確認"

        # 3. Find or create client
        client = await repo.find_client_by_name(client_name)
        if not client:
            client = await repo.create_client(Client(
                id="",
                name=client_name,
                industry=industry,
            ))

        # 4. Create deal
        deal = Deal(
            id="",
            client_id=client.id,
            title=title,
            amount=float(amount),
        )
        deal = await repo.create_deal(deal)

        # 5. Log first activity
        first_activity = SalesActivity(
            id="",
            deal_id=deal.id,
            type=ActivityTypeEnum.NOTE,
            summary=f"商機建立: {content[:200]}",
        )
        await repo.create_activity(first_activity)

        # 6. CEO escalation if amount > threshold
        if deal.amount >= CEO_ESCALATION_AMOUNT:
            await self._escalate_to_ceo(
                deal=deal,
                reason=f"高價值商機 (${deal.amount:,.0f}) 需要 CEO 關注",
            )

        await activity_repo.log(
            agent_id="SALES",
            agent_name="Sales Agent",
            activity_type=ActivityType.TASK_END,
            message=f"商機已建立: {deal.title} (${deal.amount:,.0f})",
            metadata={"deal_id": deal.id, "client_id": client.id},
        )

        return {
            "status": "created",
            "deal": deal.to_dict(),
            "client": client.to_dict(),
            "next_action": next_action,
            "validation_warnings": missing,
            "message": f"已建立商機 {deal.id}: {deal.title}",
        }

    # === Advance stage ===

    async def _handle_advance_stage(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        repo = get_sales_repo()
        deal_id = payload.get("deal_id", "")
        target_stage_str = payload.get("target_stage", "")

        deal = await repo.get_deal(deal_id)
        if not deal:
            return {"status": "error", "message": f"Deal {deal_id} not found"}

        try:
            target_stage = DealStage(target_stage_str)
        except ValueError:
            return {"status": "error", "message": f"Invalid stage: {target_stage_str}"}

        # Use dedicated close functions for terminal stages
        if target_stage == DealStage.CLOSED_WON:
            ok, reason = close_won(deal, final_price=payload.get("final_price"))
        elif target_stage == DealStage.CLOSED_LOST:
            ok, reason = close_lost(deal, reason=payload.get("lost_reason"), competitor=payload.get("lost_to_competitor"))
        else:
            ok, reason = advance_deal(deal, target_stage)
        if not ok:
            return {"status": "error", "message": reason}

        await repo.update_deal(deal)

        # Log activity
        await repo.create_activity(SalesActivity(
            id="",
            deal_id=deal.id,
            type=ActivityTypeEnum.NOTE,
            summary=f"Stage advanced to {target_stage.value}",
        ))

        activity_repo = get_activity_repo()
        await activity_repo.log(
            agent_id="SALES",
            agent_name="Sales Agent",
            activity_type=ActivityType.MILESTONE,
            message=f"商機推進: {deal.title} → {target_stage.value}",
            metadata={"deal_id": deal.id, "stage": target_stage.value},
        )

        return {
            "status": "advanced",
            "deal": deal.to_dict(),
            "message": f"{deal.title} advanced to {target_stage.value}",
        }

    # === Daily briefing ===

    async def _handle_daily_briefing(self) -> Dict[str, Any]:
        repo = get_sales_repo()
        deals = await repo.list_deals()

        # Stagnation alerts
        stagnant = detect_stagnant_deals(deals)

        # Pipeline summary
        summary = await repo.get_pipeline_summary()

        # CEO escalation for stagnant high-value deals
        for s in stagnant:
            deal = await repo.get_deal(s["deal_id"])
            if deal and deal.amount >= CEO_ESCALATION_AMOUNT:
                await self._escalate_to_ceo(
                    deal=deal,
                    reason=f"高價值商機停滯 {s['days_in_stage']} 天 (門檻 {s['threshold']} 天)",
                )
            elif deal and s["overdue_days"] >= CEO_ESCALATION_STAGNATION_DAYS:
                await self._escalate_to_ceo(
                    deal=deal,
                    reason=f"商機嚴重停滯 {s['days_in_stage']} 天",
                )

        return {
            "status": "ok",
            "pipeline_summary": summary,
            "stagnant_deals": stagnant,
            "total_stagnant": len(stagnant),
        }

    # === Generate quote ===

    async def _handle_generate_quote(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Cost-plus pricing (Phase 1)."""
        repo = get_sales_repo()
        deal_id = payload.get("deal_id", "")
        product_ids = payload.get("product_ids", [])
        margin_pct = payload.get("margin_pct", 30)  # default 30% margin

        deal = await repo.get_deal(deal_id)
        if not deal:
            return {"status": "error", "message": f"Deal {deal_id} not found"}

        products = await repo.list_products()
        selected = [p for p in products if p.id in product_ids] if product_ids else products[:1]

        total_cost = sum(p.cost_base for p in selected)
        total_price = total_cost * (1 + margin_pct / 100)
        margin = total_price - total_cost

        # Determine version
        existing_quotes = await repo.list_quotes(deal_id=deal_id)
        version = len(existing_quotes) + 1

        evidence = f"Products: {', '.join(p.name for p in selected)}; Cost: {total_cost}; Margin: {margin_pct}%"
        quote = Quote(
            id="",
            deal_id=deal_id,
            version=version,
            total_price=total_price,
            margin=margin,
            evidence_log=evidence,
        )
        quote = await repo.create_quote(quote)

        return {
            "status": "created",
            "quote": quote.to_dict(),
            "products_included": [p.to_dict() for p in selected],
            "message": f"報價 v{version} 已生成: ${total_price:,.0f}",
        }

    # === Gemini helpers ===

    async def _extract_deal_info(
        self,
        content: str,
        entities: List[Dict],
    ) -> Dict[str, Any]:
        """
        Use Gemini to extract structured deal info from free-text content.
        Falls back to entity parsing if Gemini is unavailable.
        """
        gemini = self._get_gemini()

        # Entity-based fallback values
        fallback = self._parse_entities(entities, content)

        if not gemini:
            return fallback

        prompt = f"""你是 Nexus AI Company 的業務助理。從以下 CEO 指令中提取商機資訊。

## CEO 指令
{content}

## 已解析的實體
{json.dumps(entities, ensure_ascii=False)}

## 回應格式（純 JSON）
{{
  "client_name": "公司名稱",
  "amount": 數字（台幣），
  "next_action": "下一步動作",
  "title": "商機標題",
  "industry": "產業",
  "strategy": "建議銷售策略（1-2句）"
}}

注意：
1. 金額若為「150萬」則回 1500000，「1億」回 100000000
2. 如果資訊不足，根據上下文推測合理值
3. next_action 應該是具體可執行的動作
"""

        try:
            response = gemini.generate_content(prompt)
            text = response.text.strip()
            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
            text = text.strip()
            result = json.loads(text)

            # Ensure amount is numeric
            amount = result.get("amount", 0)
            if isinstance(amount, str):
                amount = float(amount.replace(",", ""))
            result["amount"] = amount

            return result

        except Exception as e:
            logger.error(f"Gemini deal extraction failed: {e}")
            return fallback

    def _parse_entities(self, entities: List[Dict], content: str) -> Dict[str, Any]:
        """Fallback: parse entities from GATEKEEPER."""
        client_name = ""
        contact_name = ""
        amount = 0
        next_action = "待確認"

        for e in entities:
            etype = e.get("type", "")
            value = e.get("value", "")
            if etype == "company":
                client_name = value
            elif etype == "person":
                contact_name = value
            elif etype == "amount":
                try:
                    amount = float(value)
                except (ValueError, TypeError):
                    pass
            elif etype == "date":
                next_action = f"{value} 跟進"

        title = f"{client_name} 商機" if client_name else "新商機"
        if contact_name:
            next_action = next_action if next_action != "待確認" else f"聯繫 {contact_name}"

        return {
            "client_name": client_name,
            "contact_name": contact_name,
            "amount": amount,
            "next_action": next_action,
            "title": title,
            "industry": "",
        }

    # === CEO escalation ===

    async def _escalate_to_ceo(self, deal: Deal, reason: str):
        """Create a CEO Todo for escalation."""
        try:
            from app.ceo.repository import TodoRepository
            from app.ceo.models import (
                TodoItem,
                TodoAction,
                TodoType,
                TodoPriority,
            )
            from app.db.database import AsyncSessionLocal

            repo = TodoRepository(session_factory=AsyncSessionLocal)

            todo = TodoItem(
                id="",
                project_name="Sales Pipeline",
                subject=f"[SALES] {deal.title} — {reason}",
                description=f"商機 {deal.id}: {deal.title}\n金額: ${deal.amount:,.0f}\n階段: {deal.stage.value}\n原因: {reason}",
                from_agent="SALES",
                from_agent_name="Sales Agent",
                type=TodoType.NOTIFICATION,
                priority=TodoPriority.HIGH if deal.amount >= CEO_ESCALATION_AMOUNT else TodoPriority.NORMAL,
                actions=[
                    TodoAction(id="acknowledge", label="已了解", style="primary"),
                    TodoAction(id="intervene", label="我來處理", style="danger"),
                ],
                related_entity_type="deal",
                related_entity_id=deal.id,
                payload={"deal_id": deal.id, "reason": reason},
            )
            await repo.create(todo)
            logger.info(f"CEO escalation created for deal {deal.id}: {reason}")

        except Exception as e:
            logger.error(f"Failed to create CEO escalation: {e}")


# --- Lazy singleton ---

_sales_agent: Optional["SalesAgent"] = None


def get_sales_agent() -> SalesAgent:
    """Get the shared SalesAgent instance."""
    global _sales_agent
    if _sales_agent is None:
        _sales_agent = SalesAgent()
    return _sales_agent
