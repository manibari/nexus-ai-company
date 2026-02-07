"""
ORCHESTRATOR Agent

負責：
- 目標分解 (Goal Decomposition)
- 階段規劃 (Phase Planning)
- 進度追蹤 (Progress Tracking)
- 資源調度 (Resource Allocation)
- 問題升級 (Escalation)
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional

from app.goals.models import (
    Goal,
    GoalStatus,
    Phase,
    PhaseStatus,
    TimeEstimate,
    Priority,
    Checkpoint,
    ChecklistItem,
)
from app.goals.repository import GoalRepository


class OrchestratorAction(Enum):
    """ORCHESTRATOR 可執行的動作"""
    CREATE_GOAL = "create_goal"
    DECOMPOSE_GOAL = "decompose_goal"
    START_GOAL = "start_goal"
    START_PHASE = "start_phase"
    COMPLETE_PHASE = "complete_phase"
    UPDATE_PROGRESS = "update_progress"
    ESCALATE = "escalate"
    REPLAN = "replan"
    ASSIGN = "assign"


@dataclass
class PhaseTemplate:
    """階段模板"""
    name: str
    objective: str
    deliverables: List[str]
    acceptance_criteria: List[str]
    estimated_minutes: int
    buffer_minutes: int = 5
    assignee: Optional[str] = None


@dataclass
class DecompositionResult:
    """目標分解結果"""
    goal_id: str
    phases: List[Phase]
    total_estimated_minutes: int
    critical_path: List[str]
    risks: List[str]
    recommendations: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "goal_id": self.goal_id,
            "phases": [p.to_dict() for p in self.phases],
            "total_estimated_minutes": self.total_estimated_minutes,
            "critical_path": self.critical_path,
            "risks": self.risks,
            "recommendations": self.recommendations,
        }


class OrchestratorAgent:
    """
    ORCHESTRATOR Agent - 專案經理

    職責：
    1. 接收專案需求（從 GATEKEEPER 或 CEO）
    2. 分解為可執行的 Goals 和 Phases
    3. 追蹤進度
    4. 協調資源
    5. 處理阻塞和升級
    """

    # 預設階段模板（用於常見專案類型）
    PROJECT_TEMPLATES = {
        "development": [
            PhaseTemplate(
                name="需求分析",
                objective="確認需求範圍和規格",
                deliverables=["需求文件", "驗收標準"],
                acceptance_criteria=["需求已確認", "邊界已定義"],
                estimated_minutes=20,
            ),
            PhaseTemplate(
                name="系統設計",
                objective="設計系統架構和技術方案",
                deliverables=["架構圖", "技術方案"],
                acceptance_criteria=["架構已審查", "技術可行"],
                estimated_minutes=30,
            ),
            PhaseTemplate(
                name="開發實作",
                objective="完成核心功能開發",
                deliverables=["程式碼", "單元測試"],
                acceptance_criteria=["功能完成", "測試通過"],
                estimated_minutes=60,
                assignee="BUILDER",
            ),
            PhaseTemplate(
                name="測試驗證",
                objective="完成整合測試和驗收",
                deliverables=["測試報告", "修復記錄"],
                acceptance_criteria=["測試通過", "無嚴重缺陷"],
                estimated_minutes=30,
                assignee="INSPECTOR",
            ),
        ],
        "crawler": [
            PhaseTemplate(
                name="資料來源分析",
                objective="分析目標網站結構",
                deliverables=["網站分析", "資料欄位定義"],
                acceptance_criteria=["來源已確認", "欄位已定義"],
                estimated_minutes=15,
            ),
            PhaseTemplate(
                name="爬蟲開發",
                objective="開發爬蟲程式",
                deliverables=["爬蟲程式", "錯誤處理"],
                acceptance_criteria=["能正確爬取", "有重試機制"],
                estimated_minutes=30,
                assignee="BUILDER",
            ),
            PhaseTemplate(
                name="資料處理",
                objective="資料清洗和儲存",
                deliverables=["資料處理邏輯", "儲存機制"],
                acceptance_criteria=["資料正確", "可查詢"],
                estimated_minutes=20,
            ),
            PhaseTemplate(
                name="排程與監控",
                objective="設定自動執行和監控",
                deliverables=["排程設定", "監控告警"],
                acceptance_criteria=["自動執行", "異常通知"],
                estimated_minutes=15,
            ),
        ],
    }

    def __init__(self, goal_repo: Optional[GoalRepository] = None):
        self.goals = goal_repo or GoalRepository()
        self.id = "ORCHESTRATOR"
        self.name = "PM Agent"

    @property
    def agent_id(self) -> str:
        return "ORCHESTRATOR"

    @property
    def agent_name(self) -> str:
        return "PM Agent"

    async def handle(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """AgentHandler 介面實作"""
        content = payload.get("content", "")
        entities = payload.get("entities", [])
        priority = payload.get("priority", "medium")
        return await self.process_project_request(content, entities, priority)

    async def process_project_request(
        self,
        content: str,
        entities: List[Dict],
        priority: str = "medium",
    ) -> Dict[str, Any]:
        """
        處理專案需求

        Args:
            content: 專案描述
            entities: 解析出的實體
            priority: 優先級

        Returns:
            處理結果
        """
        # 1. 識別專案類型
        project_type = self._identify_project_type(content)

        # 2. 建立 Goal
        goal = Goal(
            id="",
            title=self._extract_title(content),
            objective=content[:200],
            priority=Priority(priority),
            owner=self.id,
        )

        # 3. 分解為 Phases
        phases = self._decompose_to_phases(goal, project_type)
        goal.phases = phases

        # 4. 計算時間
        total_minutes = sum(p.time_estimate.estimated_minutes for p in phases)
        goal.time_estimate = TimeEstimate(
            estimated_minutes=total_minutes,
            buffer_minutes=int(total_minutes * 0.2),  # 20% 緩衝
        )

        # 5. 儲存
        await self.goals.create(goal)

        return {
            "status": "created",
            "goal": goal.to_dict(),
            "decomposition": {
                "phases_count": len(phases),
                "total_minutes": total_minutes,
                "estimated_completion": f"{total_minutes} 分鐘",
            },
            "next_steps": [
                "確認 Goal 內容",
                "開始執行第一階段",
            ],
        }

    async def decompose_goal(
        self,
        goal_id: str,
        project_type: Optional[str] = None,
    ) -> DecompositionResult:
        """
        分解目標為階段

        Args:
            goal_id: 目標 ID
            project_type: 專案類型（可選）

        Returns:
            分解結果
        """
        goal = await self.goals.get(goal_id)
        if not goal:
            raise ValueError(f"Goal {goal_id} not found")

        # 識別專案類型
        if not project_type:
            project_type = self._identify_project_type(goal.objective)

        # 生成階段
        phases = self._decompose_to_phases(goal, project_type)

        # 更新 Goal
        goal.phases = phases
        await self.goals.update(goal)

        # 分析結果
        total_minutes = sum(p.time_estimate.estimated_minutes for p in phases)
        critical_path = [p.name for p in phases]  # 簡化：所有階段都在關鍵路徑

        risks = self._identify_decomposition_risks(phases)
        recommendations = self._generate_recommendations(goal, phases)

        return DecompositionResult(
            goal_id=goal_id,
            phases=phases,
            total_estimated_minutes=total_minutes,
            critical_path=critical_path,
            risks=risks,
            recommendations=recommendations,
        )

    async def get_status_report(self, goal_id: str) -> Dict[str, Any]:
        """
        取得目標狀態報告

        Args:
            goal_id: 目標 ID

        Returns:
            狀態報告
        """
        goal = await self.goals.get(goal_id)
        if not goal:
            return {"error": "Goal not found"}

        # 計算進度
        phases_summary = []
        for phase in goal.phases:
            phases_summary.append({
                "name": phase.name,
                "status": phase.status.value,
                "progress": phase.progress,
                "elapsed_minutes": phase.elapsed_minutes,
                "estimated_minutes": phase.time_estimate.estimated_minutes,
                "is_overdue": phase.is_overdue,
            })

        # 識別阻塞
        blockers = []
        for phase in goal.phases:
            if phase.status == PhaseStatus.BLOCKED:
                blockers.append({
                    "phase": phase.name,
                    "blockers": phase.blockers,
                })

        # 識別風險
        risks = []
        if goal.is_overdue:
            risks.append("目標已超時")
        for phase in goal.phases:
            if phase.is_overdue:
                risks.append(f"階段 {phase.name} 已超時")
        if goal.health == "at_risk":
            risks.append("目標進度落後")

        return {
            "goal": goal.to_summary(),
            "health": goal.health,
            "progress": goal.progress,
            "elapsed_minutes": goal.elapsed_minutes,
            "phases": phases_summary,
            "current_phase": goal.current_phase.name if goal.current_phase else None,
            "next_phase": goal.next_phase.name if goal.next_phase else None,
            "blockers": blockers,
            "risks": risks,
            "recommendations": self._get_progress_recommendations(goal),
        }

    async def handle_escalation(
        self,
        goal_id: str,
        issue: str,
        severity: str = "medium",
    ) -> Dict[str, Any]:
        """
        處理升級

        Args:
            goal_id: 目標 ID
            issue: 問題描述
            severity: 嚴重程度

        Returns:
            處理結果
        """
        goal = await self.goals.get(goal_id)
        if not goal:
            return {"error": "Goal not found"}

        # 記錄問題
        if goal.notes:
            goal.notes += f"\n[ESCALATION {datetime.now().isoformat()}] {issue}"
        else:
            goal.notes = f"[ESCALATION {datetime.now().isoformat()}] {issue}"

        # 根據嚴重程度決定動作
        actions = []

        if severity == "critical":
            goal.status = GoalStatus.ON_HOLD
            actions.append("目標已暫停")
            actions.append("需要 CEO 介入")
        elif severity == "high":
            actions.append("優先處理此問題")
            actions.append("調整時程")
        else:
            actions.append("記錄問題")
            actions.append("下次審查時討論")

        await self.goals.update(goal)

        return {
            "status": "escalated",
            "goal_status": goal.status.value,
            "actions_taken": actions,
            "requires_ceo_attention": severity == "critical",
        }

    async def replan(
        self,
        goal_id: str,
        reason: str,
        adjustments: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        重新規劃

        Args:
            goal_id: 目標 ID
            reason: 重新規劃原因
            adjustments: 調整內容

        Returns:
            重新規劃結果
        """
        goal = await self.goals.get(goal_id)
        if not goal:
            return {"error": "Goal not found"}

        changes = []

        # 調整時間
        if "add_buffer_minutes" in adjustments:
            extra = adjustments["add_buffer_minutes"]
            goal.time_estimate.buffer_minutes += extra
            changes.append(f"增加 {extra} 分鐘緩衝時間")

        # 調整階段
        if "extend_phase" in adjustments:
            phase_id = adjustments["extend_phase"]["phase_id"]
            extra_minutes = adjustments["extend_phase"]["minutes"]
            for phase in goal.phases:
                if phase.id == phase_id:
                    phase.time_estimate.estimated_minutes += extra_minutes
                    phase.time_estimate.buffer_minutes += int(extra_minutes * 0.1)
                    changes.append(f"階段 {phase.name} 增加 {extra_minutes} 分鐘")

        # 記錄
        note = f"[REPLAN {datetime.now().isoformat()}] {reason}"
        goal.notes = f"{goal.notes}\n{note}" if goal.notes else note

        await self.goals.update(goal)

        return {
            "status": "replanned",
            "changes": changes,
            "new_estimate": goal.time_estimate.to_dict(),
        }

    def _identify_project_type(self, content: str) -> str:
        """識別專案類型"""
        content_lower = content.lower()

        if any(kw in content_lower for kw in ["爬蟲", "crawler", "scraper", "爬取"]):
            return "crawler"
        elif any(kw in content_lower for kw in ["開發", "系統", "功能", "develop", "build"]):
            return "development"
        else:
            return "development"  # 預設

    def _extract_title(self, content: str) -> str:
        """提取標題"""
        # 取前 50 個字元作為標題
        lines = content.strip().split('\n')
        first_line = lines[0] if lines else content[:50]
        return first_line[:50] + ("..." if len(first_line) > 50 else "")

    def _decompose_to_phases(
        self,
        goal: Goal,
        project_type: str,
    ) -> List[Phase]:
        """分解為階段"""
        templates = self.PROJECT_TEMPLATES.get(project_type, self.PROJECT_TEMPLATES["development"])

        phases = []
        for i, template in enumerate(templates):
            phase = Phase(
                id="",
                goal_id=goal.id,
                name=template.name,
                objective=template.objective,
                sequence=i,
                deliverables=template.deliverables,
                acceptance_criteria=template.acceptance_criteria,
                time_estimate=TimeEstimate(
                    estimated_minutes=template.estimated_minutes,
                    buffer_minutes=template.buffer_minutes,
                ),
                assignee=template.assignee,
            )
            phases.append(phase)

        return phases

    def _identify_decomposition_risks(self, phases: List[Phase]) -> List[str]:
        """識別分解風險"""
        risks = []

        total_time = sum(p.time_estimate.estimated_minutes for p in phases)
        if total_time > 120:
            risks.append("總時間超過 2 小時，建議分階段執行")

        unassigned = [p for p in phases if not p.assignee]
        if unassigned:
            risks.append(f"{len(unassigned)} 個階段尚未指派執行者")

        return risks

    def _generate_recommendations(self, goal: Goal, phases: List[Phase]) -> List[str]:
        """生成建議"""
        recommendations = []

        if goal.priority == Priority.CRITICAL:
            recommendations.append("建議全程監控進度")

        if len(phases) > 5:
            recommendations.append("階段較多，建議設定中間檢查點")

        return recommendations

    def _get_progress_recommendations(self, goal: Goal) -> List[str]:
        """取得進度建議"""
        recommendations = []

        if goal.health == "at_risk":
            recommendations.append("進度落後，建議加速或調整時程")

        if goal.is_overdue:
            recommendations.append("已超時，需要重新評估並與 CEO 溝通")

        current = goal.current_phase
        if current and current.is_overdue:
            recommendations.append(f"當前階段 {current.name} 已超時")

        next_phase = goal.next_phase
        if next_phase:
            recommendations.append(f"下一階段：{next_phase.name}")

        return recommendations


# 全域實例
_orchestrator = OrchestratorAgent()


async def process_project(content: str, entities: List[Dict], priority: str = "medium") -> Dict:
    """便利函數：處理專案"""
    return await _orchestrator.process_project_request(content, entities, priority)


async def get_goal_status(goal_id: str) -> Dict:
    """便利函數：取得目標狀態"""
    return await _orchestrator.get_status_report(goal_id)
