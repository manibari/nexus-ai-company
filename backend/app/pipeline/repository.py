"""
Sales Pipeline Repository

In-memory 儲存（Tracer Bullet 版本）
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from app.pipeline.models import (
    Opportunity,
    OpportunityStage,
    OpportunityStatus,
    Contact,
    ContactRole,
    Activity,
    ActivityType,
    MEDDICScore,
    STAGE_PROBABILITIES,
)


class PipelineRepository:
    """Pipeline 儲存庫"""

    def __init__(self):
        self._opportunities: Dict[str, Opportunity] = {}
        self._activities: Dict[str, List[Activity]] = {}  # opp_id -> activities

    # === Opportunity CRUD ===

    async def create_opportunity(self, opp: Opportunity) -> Opportunity:
        """建立商機"""
        self._opportunities[opp.id] = opp
        self._activities[opp.id] = []
        return opp

    async def get_opportunity(self, opp_id: str) -> Optional[Opportunity]:
        """取得商機"""
        return self._opportunities.get(opp_id)

    async def update_opportunity(self, opp: Opportunity) -> Opportunity:
        """更新商機"""
        self._opportunities[opp.id] = opp
        return opp

    async def delete_opportunity(self, opp_id: str) -> bool:
        """刪除商機"""
        if opp_id in self._opportunities:
            del self._opportunities[opp_id]
            if opp_id in self._activities:
                del self._activities[opp_id]
            return True
        return False

    async def list_opportunities(
        self,
        stage: Optional[OpportunityStage] = None,
        status: Optional[OpportunityStatus] = None,
        owner: Optional[str] = None,
        limit: int = 50,
    ) -> List[Opportunity]:
        """列出商機"""
        results = list(self._opportunities.values())

        if stage:
            results = [o for o in results if o.stage == stage]
        if status:
            results = [o for o in results if o.status == status]
        if owner:
            results = [o for o in results if o.owner == owner]

        # 按建立時間排序（最新的在前）
        results.sort(key=lambda o: o.created_at, reverse=True)

        return results[:limit]

    async def list_open_opportunities(self) -> List[Opportunity]:
        """列出所有開放中的商機"""
        return await self.list_opportunities(status=OpportunityStatus.OPEN)

    # === Stage Operations ===

    async def advance_stage(self, opp_id: str) -> Optional[Opportunity]:
        """推進階段"""
        opp = await self.get_opportunity(opp_id)
        if opp:
            new_stage = opp.advance_stage()
            if new_stage:
                await self.update_opportunity(opp)
                return opp
        return None

    async def set_stage(
        self,
        opp_id: str,
        stage: OpportunityStage
    ) -> Optional[Opportunity]:
        """設定階段"""
        opp = await self.get_opportunity(opp_id)
        if opp:
            opp.stage = stage
            opp.stage_entered_at = datetime.utcnow()
            if stage == OpportunityStage.WON:
                opp.status = OpportunityStatus.WON
            elif stage == OpportunityStage.LOST:
                opp.status = OpportunityStatus.LOST
            await self.update_opportunity(opp)
            return opp
        return None

    async def mark_won(self, opp_id: str) -> Optional[Opportunity]:
        """標記成交"""
        return await self.set_stage(opp_id, OpportunityStage.WON)

    async def mark_lost(
        self,
        opp_id: str,
        reason: Optional[str] = None
    ) -> Optional[Opportunity]:
        """標記失敗"""
        opp = await self.get_opportunity(opp_id)
        if opp:
            opp.stage = OpportunityStage.LOST
            opp.status = OpportunityStatus.LOST
            opp.lost_reason = reason
            await self.update_opportunity(opp)
            return opp
        return None

    # === Contact Operations ===

    async def add_contact(
        self,
        opp_id: str,
        contact: Contact
    ) -> Optional[Contact]:
        """新增聯絡人"""
        opp = await self.get_opportunity(opp_id)
        if opp:
            opp.contacts.append(contact)

            # 自動更新 MEDDIC
            if contact.role == ContactRole.CHAMPION:
                opp.meddic.champion_identified = True
                opp.meddic.champion_name = contact.name
                opp.meddic.champion_title = contact.title
                if not opp.meddic.champion_score:
                    opp.meddic.champion_score = 5

            elif contact.role == ContactRole.ECONOMIC_BUYER:
                opp.meddic.eb_identified = True
                opp.meddic.eb_name = contact.name
                if not opp.meddic.eb_score:
                    opp.meddic.eb_score = 3
                    opp.meddic.eb_access_level = "identified"

            await self.update_opportunity(opp)
            return contact
        return None

    async def update_contact(
        self,
        opp_id: str,
        contact_id: str,
        updates: Dict[str, Any]
    ) -> Optional[Contact]:
        """更新聯絡人"""
        opp = await self.get_opportunity(opp_id)
        if opp:
            for contact in opp.contacts:
                if contact.id == contact_id:
                    for key, value in updates.items():
                        if hasattr(contact, key):
                            setattr(contact, key, value)
                    await self.update_opportunity(opp)
                    return contact
        return None

    # === Activity Operations ===

    async def add_activity(self, activity: Activity) -> Activity:
        """新增活動"""
        opp_id = activity.opportunity_id
        if opp_id not in self._activities:
            self._activities[opp_id] = []
        self._activities[opp_id].append(activity)

        # 更新商機的最後活動時間
        opp = await self.get_opportunity(opp_id)
        if opp:
            opp.last_activity_at = activity.occurred_at
            await self.update_opportunity(opp)

        return activity

    async def get_activities(
        self,
        opp_id: str,
        limit: int = 20
    ) -> List[Activity]:
        """取得活動列表"""
        activities = self._activities.get(opp_id, [])
        # 按時間排序（最新的在前）
        activities.sort(key=lambda a: a.occurred_at, reverse=True)
        return activities[:limit]

    # === MEDDIC Operations ===

    async def update_meddic(
        self,
        opp_id: str,
        updates: Dict[str, Any]
    ) -> Optional[MEDDICScore]:
        """更新 MEDDIC 分數"""
        opp = await self.get_opportunity(opp_id)
        if opp:
            meddic = opp.meddic

            if "pain_score" in updates:
                meddic.pain_score = updates["pain_score"]
            if "pain_identified" in updates:
                meddic.pain_identified = updates["pain_identified"]
            if "pain_description" in updates:
                meddic.pain_description = updates["pain_description"]

            if "champion_score" in updates:
                meddic.champion_score = updates["champion_score"]
            if "champion_identified" in updates:
                meddic.champion_identified = updates["champion_identified"]

            if "eb_score" in updates:
                meddic.eb_score = updates["eb_score"]
            if "eb_identified" in updates:
                meddic.eb_identified = updates["eb_identified"]
            if "eb_access_level" in updates:
                meddic.eb_access_level = updates["eb_access_level"]

            await self.update_opportunity(opp)
            return meddic
        return None

    # === Dashboard / Statistics ===

    def get_pipeline_summary(self) -> Dict[str, Any]:
        """取得 Pipeline 摘要"""
        all_opps = list(self._opportunities.values())
        open_opps = [o for o in all_opps if o.status == OpportunityStatus.OPEN]

        # 按階段分組
        by_stage: Dict[str, List[Opportunity]] = {}
        for stage in OpportunityStage:
            by_stage[stage.value] = [
                o for o in open_opps if o.stage == stage
            ]

        # 計算各階段統計
        stage_stats = {}
        for stage_value, opps in by_stage.items():
            stage_stats[stage_value] = {
                "count": len(opps),
                "total_amount": sum(o.amount or 0 for o in opps),
                "weighted_amount": sum(o.weighted_amount for o in opps),
            }

        # 總計
        total_open = len(open_opps)
        total_amount = sum(o.amount or 0 for o in open_opps)
        total_weighted = sum(o.weighted_amount for o in open_opps)

        # 警告
        stale_opps = [o for o in open_opps if o.is_stale]
        at_risk = [o for o in open_opps if o.meddic.health in ["at_risk", "needs_attention", "weak"]]

        return {
            "total_open": total_open,
            "total_amount": total_amount,
            "total_weighted_amount": total_weighted,
            "by_stage": stage_stats,
            "alerts": {
                "stale_count": len(stale_opps),
                "stale_opportunities": [o.to_summary() for o in stale_opps],
                "at_risk_count": len(at_risk),
                "at_risk_opportunities": [o.to_summary() for o in at_risk],
            },
            "won_this_month": len([
                o for o in all_opps
                if o.status == OpportunityStatus.WON
                and o.stage_entered_at.month == datetime.utcnow().month
            ]),
            "lost_this_month": len([
                o for o in all_opps
                if o.status == OpportunityStatus.LOST
                and o.stage_entered_at.month == datetime.utcnow().month
            ]),
        }

    def get_statistics(self) -> Dict[str, Any]:
        """取得統計資訊"""
        all_opps = list(self._opportunities.values())

        won = [o for o in all_opps if o.status == OpportunityStatus.WON]
        lost = [o for o in all_opps if o.status == OpportunityStatus.LOST]
        open_opps = [o for o in all_opps if o.status == OpportunityStatus.OPEN]

        win_rate = len(won) / (len(won) + len(lost)) if (len(won) + len(lost)) > 0 else 0

        return {
            "total": len(all_opps),
            "open": len(open_opps),
            "won": len(won),
            "lost": len(lost),
            "win_rate": round(win_rate * 100, 1),
            "total_won_amount": sum(o.amount or 0 for o in won),
            "average_deal_size": sum(o.amount or 0 for o in won) / len(won) if won else 0,
            "pipeline_value": sum(o.amount or 0 for o in open_opps),
            "weighted_pipeline": sum(o.weighted_amount for o in open_opps),
        }
