"""
ORCHESTRATOR Agent（司禮監）

Issue #15: 升級為 TaskOrchestrator，整合 Task Lifecycle 狀態機。
Issue #16: Output Governance — Agent 產出 Schema Check + Rule Check。

職責：
- Execution Plan 生成（Gemini LLM）
- Routing Governance（第一層治理：風險評估 → 自動放行 / CEO 審核）
- Output Governance（第二層治理：Schema Check → Rule Check → 自動核准 / CEO 審核）
- 狀態機驅動：submitted → planning → ... → draft_approved / draft_review
- Plan 核准後 dispatch 到 Domain Agent(s)，收回結果後驅動 Output Governance

保留舊有 Goal Decomposition 功能（向後相容）。
"""

import json
import logging
import os
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

logger = logging.getLogger(__name__)

# Routing Governance 門檻
AUTO_APPROVE_RISK_THRESHOLD = 0.3


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
    ORCHESTRATOR Agent — 司禮監

    Issue #15: 升級為流程控制中樞。

    新流程（handle with task_id）:
    1. 接收 payload（含 task_id / trace_id）
    2. 驅動狀態機：submitted → planning
    3. Gemini 生成 Execution Plan
    4. Routing Governance：risk < 0.3 自動放行，≥ 0.3 → CEO 審核
    5. Plan 核准後 dispatch 到 Domain Agent(s)

    舊流程（handle without task_id）:
    - 保留 Goal Decomposition（向後相容）
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

    # Intent → Agent 對應
    INTENT_AGENT_MAP = {
        "product_feature": "PM",
        "product_bug": "QA",
        "opportunity": "SALES",
        "project": "PM",
        "task": "PM",
    }

    def __init__(self, goal_repo: Optional[GoalRepository] = None):
        self.goals = goal_repo or GoalRepository()
        self.id = "ORCHESTRATOR"
        self.name = "司禮監"
        self._gemini_client = None

    @property
    def agent_id(self) -> str:
        return "ORCHESTRATOR"

    @property
    def agent_name(self) -> str:
        return "司禮監"

    # ================================================================
    # AgentHandler 介面
    # ================================================================

    async def handle(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        AgentHandler 介面實作。

        如果 payload 包含 task_id → 走 lifecycle 流程（Issue #15）
        否則 → 走舊的 Goal Decomposition（向後相容）
        """
        task_id = payload.get("task_id")

        if task_id:
            return await self._handle_lifecycle(payload)
        else:
            # 向後相容：舊的 Goal Decomposition
            content = payload.get("content", "")
            entities = payload.get("entities", [])
            priority = payload.get("priority", "medium")
            return await self.process_project_request(content, entities, priority)

    # ================================================================
    # Issue #15: Lifecycle 流程
    # ================================================================

    async def _handle_lifecycle(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Task Lifecycle 流程：

        1. submitted → planning（start_planning）
        2. Gemini 生成 Execution Plan
        3. 儲存 Plan + 記錄 event
        4. 評估 routing_risk
        5. risk < 0.3 → auto_approve_plan → plan_approved
        6. risk ≥ 0.3 → request_plan_review → CEO Todo
        """
        from app.task.repository import get_task_repo
        from app.core.task_state_machine import TaskLifecycle
        from app.agents.activity_log import ActivityType, get_activity_repo

        task_id = payload["task_id"]
        trace_id = payload.get("trace_id")
        content = payload.get("content", "")
        intent = payload.get("intent", "")
        entities = payload.get("entities", [])

        repo = get_task_repo()
        activity_repo = get_activity_repo()

        # 記錄活動開始
        await activity_repo.log(
            agent_id="ORCHESTRATOR",
            agent_name="司禮監",
            activity_type=ActivityType.TASK_START,
            message=f"開始編排任務: {content[:60]}...",
            metadata={"task_id": task_id, "intent": intent},
        )

        # 1. submitted → planning
        task = await repo.get_task(task_id)
        if not task:
            return {"status": "error", "message": f"Task {task_id} not found"}

        machine = TaskLifecycle(initial_state=task["lifecycle_status"])
        ok, result = machine.try_trigger("start_planning")
        if not ok:
            logger.warning(f"Cannot start_planning for {task_id}: {result}")
            return {"status": "error", "message": result}

        await repo.update_lifecycle_status(task_id, "planning")
        await repo.record_event(
            task_id=task_id,
            event_type="TRANSITION_START_PLANNING",
            actor="agent:ORCHESTRATOR",
            from_status="submitted",
            to_status="planning",
            trace_id=trace_id,
        )

        # 2. Gemini 生成 Execution Plan
        plan_data = await self._generate_execution_plan(content, intent, entities)
        routing_risk = plan_data.get("routing_risk_score", 0.5)
        risk_factors = plan_data.get("risk_factors", [])

        # 3. 儲存 Plan
        saved_plan = await repo.save_execution_plan(
            task_id=task_id,
            plan_json=plan_data,
            routing_risk=routing_risk,
            risk_factors=risk_factors,
        )

        await repo.record_event(
            task_id=task_id,
            event_type="PLAN_GENERATED",
            actor="agent:ORCHESTRATOR",
            from_status="planning",
            to_status="planning",
            payload={
                "plan_id": saved_plan["id"],
                "plan_version": saved_plan["version"],
                "routing_risk": routing_risk,
            },
            trace_id=trace_id,
        )

        # 4. Routing Governance
        is_auto = self._is_auto_approvable(plan_data, routing_risk)

        if is_auto:
            # 自動放行：planning → plan_approved
            machine2 = TaskLifecycle(initial_state="planning")
            machine2.auto_approve_plan()

            await repo.update_lifecycle_status(task_id, "plan_approved")
            await repo.record_event(
                task_id=task_id,
                event_type="PLAN_AUTO_APPROVED",
                actor="system:routing_governance",
                from_status="planning",
                to_status="plan_approved",
                payload={"routing_risk": routing_risk, "reason": "auto_approve_eligible"},
                trace_id=trace_id,
            )

            await activity_repo.log(
                agent_id="ORCHESTRATOR",
                agent_name="司禮監",
                activity_type=ActivityType.MILESTONE,
                message=f"執行計畫自動放行（風險 {routing_risk:.2f}）",
                metadata={"task_id": task_id, "plan_id": saved_plan["id"]},
            )

            # 自動放行後 dispatch 到目標 Agent
            dispatch_result = await self._dispatch_plan_steps(task_id, plan_data, payload, trace_id)

            return {
                "status": "plan_auto_approved",
                "task_id": task_id,
                "plan_id": saved_plan["id"],
                "routing_risk": routing_risk,
                "auto_approved": True,
                "dispatch_result": dispatch_result,
            }
        else:
            # 需要 CEO 審核：planning → plan_review
            machine3 = TaskLifecycle(initial_state="planning")
            machine3.request_plan_review()

            await repo.update_lifecycle_status(task_id, "plan_review")
            await repo.record_event(
                task_id=task_id,
                event_type="PLAN_PENDING_REVIEW",
                actor="system:routing_governance",
                from_status="planning",
                to_status="plan_review",
                payload={"routing_risk": routing_risk, "risk_factors": risk_factors},
                trace_id=trace_id,
            )

            # 建立 CEO Todo
            todo = await self._create_plan_review_todo(
                task_id=task_id,
                plan=plan_data,
                plan_id=saved_plan["id"],
                routing_risk=routing_risk,
                risk_factors=risk_factors,
                content=content,
            )

            # WS broadcast
            await self._broadcast_plan_review(task_id, routing_risk, trace_id)

            await activity_repo.log(
                agent_id="ORCHESTRATOR",
                agent_name="司禮監",
                activity_type=ActivityType.MILESTONE,
                message=f"執行計畫需 CEO 審核（風險 {routing_risk:.2f}）",
                metadata={"task_id": task_id, "plan_id": saved_plan["id"]},
            )

            return {
                "status": "plan_pending_review",
                "task_id": task_id,
                "plan_id": saved_plan["id"],
                "routing_risk": routing_risk,
                "risk_factors": risk_factors,
                "auto_approved": False,
                "todo_id": todo.id if todo else None,
            }

    # ================================================================
    # Gemini: Execution Plan 生成
    # ================================================================

    def _get_gemini(self):
        """延遲初始化 Gemini client"""
        if self._gemini_client is None:
            import google.generativeai as genai
            api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
            if not api_key:
                logger.warning("No Gemini API key found")
                return None
            genai.configure(api_key=api_key)
            self._gemini_client = genai.GenerativeModel("gemini-2.5-flash")
        return self._gemini_client

    async def _generate_execution_plan(
        self,
        content: str,
        intent: str,
        entities: List[Dict],
    ) -> Dict[str, Any]:
        """使用 Gemini 生成 Execution Plan"""
        gemini = self._get_gemini()

        entities_text = ", ".join(
            f"{e.get('entity_type', e.get('type', ''))}: {e.get('value', '')}"
            for e in entities
        ) if entities else "無"

        if not gemini:
            return self._fallback_execution_plan(content, intent, entities)

        prompt = f"""你是 Nexus AI Company 的司禮監（TaskOrchestrator），負責分析 CEO 指令並規劃執行方案。

## CEO 指令
{content}

## 意圖分析
- Intent: {intent}
- 實體: {entities_text}

## 可用 Agent
- PM: 產品經理，負責需求分析、PRD、產品規劃
- SALES: 業務，負責商機分析、MEDDIC、報價
- DEVELOPER: 工程師，負責技術方案、開發實作
- QA: 品質保證，負責測試計畫、驗收測試

## 輸出格式（純 JSON）
{{
  "interpreted_as": "一句話說明你理解的任務",
  "routing_risk_score": 0.5,
  "auto_approve_eligible": false,
  "risk_factors": [
    "風險因素 1",
    "風險因素 2"
  ],
  "execution_plan": {{
    "steps": [
      {{
        "order": 1,
        "agent": "PM",
        "sub_task": "具體要做什麼",
        "estimated_tokens": 3000,
        "depends_on": []
      }}
    ],
    "total_estimated_tokens": 3000
  }}
}}

## 評分規則
routing_risk_score 評分：
- 0.0-0.2: 純內部、低風險、單 Agent
- 0.2-0.4: 內部但涉及多步驟
- 0.4-0.6: 涉及對外操作（發信、報價等）
- 0.6-0.8: 金額超過 100 萬、涉及部署
- 0.8-1.0: 涉及刪除、不可逆操作

auto_approve_eligible = true 當：
- routing_risk_score < 0.3
- 單一 Agent
- 不涉及對外操作、金額、部署
"""

        try:
            response = gemini.generate_content(prompt)
            text = response.text.strip()

            # 清理 markdown
            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
            text = text.strip()

            plan = json.loads(text)
            return plan

        except Exception as e:
            logger.error(f"Gemini plan generation failed: {e}")
            return self._fallback_execution_plan(content, intent, entities)

    def _fallback_execution_plan(
        self,
        content: str,
        intent: str,
        entities: List[Dict],
    ) -> Dict[str, Any]:
        """Gemini 不可用時的 fallback plan"""
        target_agent = self.INTENT_AGENT_MAP.get(intent, "PM")

        return {
            "interpreted_as": f"[{intent}] {content[:100]}",
            "routing_risk_score": 0.5,
            "auto_approve_eligible": False,
            "risk_factors": ["Gemini 不可用，使用 fallback 計畫，需人工審核"],
            "execution_plan": {
                "steps": [
                    {
                        "order": 1,
                        "agent": target_agent,
                        "sub_task": content[:200],
                        "estimated_tokens": 3000,
                        "depends_on": [],
                    }
                ],
                "total_estimated_tokens": 3000,
            },
        }

    # ================================================================
    # Routing Governance
    # ================================================================

    def _is_auto_approvable(self, plan: Dict, routing_risk: float) -> bool:
        """判斷是否自動放行"""
        if routing_risk >= AUTO_APPROVE_RISK_THRESHOLD:
            return False

        if not plan.get("auto_approve_eligible", False):
            return False

        steps = plan.get("execution_plan", {}).get("steps", [])
        if len(steps) > 1:
            return False

        return True

    async def _create_plan_review_todo(
        self,
        task_id: str,
        plan: Dict,
        plan_id: str,
        routing_risk: float,
        risk_factors: List[str],
        content: str,
    ):
        """建立 CEO Plan Review 待辦"""
        try:
            from app.ceo.models import TodoItem, TodoAction, TodoType, TodoPriority
            from app.api.ceo_todo import _get_repo

            interpreted = plan.get("interpreted_as", content[:80])
            steps = plan.get("execution_plan", {}).get("steps", [])
            steps_desc = "\n".join(
                f"  {s['order']}. [{s['agent']}] {s['sub_task']}"
                for s in steps
            )
            risks_desc = "\n".join(f"  - {r}" for r in risk_factors)

            todo = TodoItem(
                id="",
                project_name="Task Lifecycle",
                subject=f"[司禮監] 執行計畫待審核: {interpreted[:60]}",
                description=(
                    f"任務: {interpreted}\n"
                    f"風險分數: {routing_risk:.2f}\n\n"
                    f"執行步驟:\n{steps_desc}\n\n"
                    f"風險因素:\n{risks_desc}"
                ),
                from_agent="ORCHESTRATOR",
                from_agent_name="司禮監",
                type=TodoType.APPROVAL,
                priority=TodoPriority.HIGH if routing_risk >= 0.5 else TodoPriority.NORMAL,
                actions=[
                    TodoAction(id="approve", label="核准執行", style="primary"),
                    TodoAction(
                        id="approve_with_comment",
                        label="核准並備註",
                        style="primary",
                        requires_input=True,
                        input_placeholder="補充指示...",
                    ),
                    TodoAction(
                        id="revise",
                        label="要求修改",
                        style="default",
                        requires_input=True,
                        input_placeholder="修改要求...",
                    ),
                    TodoAction(id="reject", label="駁回", style="danger"),
                ],
                related_entity_type="task",
                related_entity_id=task_id,
                payload={
                    "task_id": task_id,
                    "plan_id": plan_id,
                    "routing_risk": routing_risk,
                    "execution_plan": plan,
                    "callback_endpoint": f"/api/v1/task/{task_id}/plan/approve",
                },
            )

            todo_repo = _get_repo()
            await todo_repo.create(todo)
            logger.info(f"Created plan review todo: {todo.id} for task {task_id}")
            return todo

        except Exception as e:
            logger.error(f"Failed to create plan review todo: {e}")
            return None

    async def _broadcast_plan_review(self, task_id: str, routing_risk: float, trace_id: str):
        """WS 通知：有新的執行計畫待審核"""
        try:
            from app.agents.ws_manager import get_ws_manager
            mgr = get_ws_manager()
            if mgr:
                await mgr.broadcast({
                    "type": "task_lifecycle",
                    "task_id": task_id,
                    "lifecycle_status": "plan_review",
                    "routing_risk": routing_risk,
                    "trace_id": trace_id,
                    "message": "有新的執行計畫待審核",
                })
        except Exception as e:
            logger.warning(f"WS broadcast failed: {e}")

    # ================================================================
    # Plan 核准後 dispatch
    # ================================================================

    async def _dispatch_plan_steps(
        self,
        task_id: str,
        plan: Dict,
        original_payload: Dict,
        trace_id: str,
    ) -> Dict[str, Any]:
        """Plan 核准後，依序 dispatch 到目標 Agent(s)"""
        from app.agents.registry import get_registry
        from app.task.repository import get_task_repo
        from app.core.task_state_machine import TaskLifecycle

        repo = get_task_repo()
        steps = plan.get("execution_plan", {}).get("steps", [])

        if not steps:
            return {"status": "no_steps"}

        # plan_approved → reasoning
        machine = TaskLifecycle(initial_state="plan_approved")
        ok, _ = machine.try_trigger("start_reasoning")
        if ok:
            await repo.update_lifecycle_status(task_id, "reasoning")
            await repo.record_event(
                task_id=task_id,
                event_type="TRANSITION_START_REASONING",
                actor="agent:ORCHESTRATOR",
                from_status="plan_approved",
                to_status="reasoning",
                trace_id=trace_id,
            )

        # dispatch 第一步（sequential：目前只 dispatch 第一步）
        first_step = steps[0]
        target_agent = first_step.get("agent", "PM")

        registry = get_registry()

        dispatch_payload = {
            "content": original_payload.get("content", ""),
            "entities": original_payload.get("entities", []),
            "intake_id": original_payload.get("intake_id"),
            "intent": original_payload.get("intent"),
            "sub_task": first_step.get("sub_task", ""),
            "task_id": task_id,
            "trace_id": trace_id,
        }

        dispatch_result = await registry.dispatch(
            target_id=target_agent,
            payload=dispatch_payload,
            from_agent="ORCHESTRATOR",
        )

        # Issue #16: Output Governance — 收回 Agent 結果，驅動 Schema + Rule Check
        if dispatch_result.get("status") != "error":
            governance_result = await self._process_agent_result(
                task_id=task_id,
                agent_id=target_agent,
                agent_result=dispatch_result,
                plan_data=plan,
                trace_id=trace_id,
            )
        else:
            governance_result = {
                "status": "agent_error",
                "message": dispatch_result.get("message"),
            }

        return {
            "status": "dispatched",
            "target_agent": target_agent,
            "step_order": first_step.get("order", 1),
            "dispatch_status": dispatch_result.get("status"),
            "output_governance": governance_result,
        }

    # ================================================================
    # Issue #16: Output Governance — Agent 結果回收
    # ================================================================

    async def _process_agent_result(
        self,
        task_id: str,
        agent_id: str,
        agent_result: Dict[str, Any],
        plan_data: Dict[str, Any],
        trace_id: str,
    ) -> Dict[str, Any]:
        """
        Agent 完成後的 Output Governance 流程：

        1. reasoning → draft_generated（draft_ready）
        2. draft_generated → schema_check（check_schema）
        3. Schema 驗證
           - pass → schema_check → rule_check（schema_pass）
           - fail + retry < 3 → schema_check → reasoning（schema_fail_retry）
           - fail + retry ≥ 3 → schema_check → escalated（schema_fail_final）
        4. Rule Check
           - auto_approve → rule_check → draft_approved（auto_approve_draft）
           - needs_review → rule_check → draft_review（request_draft_review）+ CEO Todo
        """
        from app.core.output_governance import validate_schema, check_rules
        from app.task.repository import get_task_repo
        from app.agents.activity_log import ActivityType, get_activity_repo

        repo = get_task_repo()
        activity_repo = get_activity_repo()
        task = await repo.get_task(task_id)
        if not task:
            return {"status": "error", "message": f"Task {task_id} not found"}

        retry_count = task.get("retry_count", 0)

        # 1. reasoning → draft_generated
        await self._transition(task_id, "draft_ready", "reasoning", "draft_generated", trace_id)

        # 2. draft_generated → schema_check
        await self._transition(task_id, "check_schema", "draft_generated", "schema_check", trace_id)

        # 3. Schema Check
        schema_passed, schema_errors = validate_schema(agent_id, agent_result)

        if not schema_passed:
            await activity_repo.log(
                agent_id="ORCHESTRATOR",
                agent_name="司禮監",
                activity_type=ActivityType.ERROR,
                message=f"Schema 驗證失敗 ({agent_id}): {', '.join(schema_errors[:3])}",
                metadata={"task_id": task_id, "errors": schema_errors, "retry_count": retry_count},
            )

            if retry_count < 2:
                # schema_fail_retry → reasoning（retry_count + 1）
                new_retry = retry_count + 1
                await repo.update_lifecycle_status(task_id, "reasoning", retry_count=new_retry)
                await repo.record_event(
                    task_id=task_id,
                    event_type="TRANSITION_SCHEMA_FAIL_RETRY",
                    actor="system:output_governance",
                    from_status="schema_check",
                    to_status="reasoning",
                    payload={"errors": schema_errors, "retry_count": new_retry},
                    trace_id=trace_id,
                )
                return {
                    "status": "schema_failed_retry",
                    "errors": schema_errors,
                    "retry_count": new_retry,
                }
            else:
                # schema_fail_final → escalated
                await self._transition(
                    task_id, "schema_fail_final", "schema_check", "escalated", trace_id,
                    payload={"errors": schema_errors, "retry_count": retry_count},
                )
                return {
                    "status": "escalated",
                    "reason": "schema_check_exhausted",
                    "errors": schema_errors,
                }

        # 4. schema_pass → rule_check
        await self._transition(task_id, "schema_pass", "schema_check", "rule_check", trace_id)

        await activity_repo.log(
            agent_id="ORCHESTRATOR",
            agent_name="司禮監",
            activity_type=ActivityType.MILESTONE,
            message=f"Schema 驗證通過 ({agent_id})，進入 Rule Check",
            metadata={"task_id": task_id, "agent_id": agent_id},
        )

        # 5. Rule Check
        auto_approve, risk_score, reasons = check_rules(agent_id, agent_result, plan_data)

        if auto_approve:
            # auto_approve_draft → draft_approved
            await self._transition(
                task_id, "auto_approve_draft", "rule_check", "draft_approved", trace_id,
                payload={"risk_score": risk_score, "reasons": reasons},
            )
            await activity_repo.log(
                agent_id="ORCHESTRATOR",
                agent_name="司禮監",
                activity_type=ActivityType.MILESTONE,
                message=f"Draft 自動核准（風險 {risk_score:.2f}）",
                metadata={"task_id": task_id, "agent_id": agent_id, "risk_score": risk_score},
            )
            return {
                "status": "draft_auto_approved",
                "task_id": task_id,
                "agent_id": agent_id,
                "risk_score": risk_score,
                "reasons": reasons,
            }
        else:
            # request_draft_review → draft_review
            await self._transition(
                task_id, "request_draft_review", "rule_check", "draft_review", trace_id,
                payload={"risk_score": risk_score, "reasons": reasons},
            )

            # 建立 CEO Draft Review Todo
            todo = await self._create_draft_review_todo(
                task_id=task_id,
                agent_id=agent_id,
                agent_result=agent_result,
                risk_score=risk_score,
                reasons=reasons,
            )

            # WS broadcast
            await self._broadcast_draft_review(task_id, agent_id, risk_score, trace_id)

            await activity_repo.log(
                agent_id="ORCHESTRATOR",
                agent_name="司禮監",
                activity_type=ActivityType.MILESTONE,
                message=f"Draft 需 CEO 審核（風險 {risk_score:.2f}）",
                metadata={"task_id": task_id, "agent_id": agent_id, "risk_score": risk_score},
            )

            return {
                "status": "draft_pending_review",
                "task_id": task_id,
                "agent_id": agent_id,
                "risk_score": risk_score,
                "reasons": reasons,
                "todo_id": todo.id if todo else None,
            }

    async def _transition(
        self,
        task_id: str,
        trigger: str,
        from_status: str,
        to_status: str,
        trace_id: str,
        payload: Optional[Dict] = None,
    ):
        """輔助：執行 lifecycle 轉換（更新 DB + 記錄 event）"""
        from app.task.repository import get_task_repo

        repo = get_task_repo()
        await repo.update_lifecycle_status(task_id, to_status)
        await repo.record_event(
            task_id=task_id,
            event_type=f"TRANSITION_{trigger.upper()}",
            actor="agent:ORCHESTRATOR",
            from_status=from_status,
            to_status=to_status,
            payload=payload,
            trace_id=trace_id,
        )

    async def _create_draft_review_todo(
        self,
        task_id: str,
        agent_id: str,
        agent_result: Dict[str, Any],
        risk_score: float,
        reasons: List[str],
    ):
        """建立 CEO Draft Review 待辦"""
        try:
            from app.ceo.models import TodoItem, TodoAction, TodoType, TodoPriority
            from app.api.ceo_todo import _get_repo

            # 摘要 agent 結果
            agent_status = agent_result.get("status", "unknown")
            agent_message = agent_result.get("message", "")[:200]
            reasons_desc = "\n".join(f"  - {r}" for r in reasons)

            todo = TodoItem(
                id="",
                project_name="Task Lifecycle",
                subject=f"[司禮監] Draft 待審核: {agent_id} → {agent_status}",
                description=(
                    f"Agent: {agent_id}\n"
                    f"狀態: {agent_status}\n"
                    f"風險分數: {risk_score:.2f}\n\n"
                    f"Agent 回覆: {agent_message}\n\n"
                    f"治理分析:\n{reasons_desc}"
                ),
                from_agent="ORCHESTRATOR",
                from_agent_name="司禮監",
                type=TodoType.APPROVAL,
                priority=TodoPriority.HIGH if risk_score >= 0.5 else TodoPriority.NORMAL,
                actions=[
                    TodoAction(id="approve_draft", label="核准 Draft", style="primary"),
                    TodoAction(
                        id="revise_draft",
                        label="要求修改",
                        style="default",
                        requires_input=True,
                        input_placeholder="修改要求...",
                    ),
                    TodoAction(id="reject_draft", label="駁回", style="danger"),
                ],
                related_entity_type="task",
                related_entity_id=task_id,
                payload={
                    "task_id": task_id,
                    "agent_id": agent_id,
                    "risk_score": risk_score,
                    "agent_result_status": agent_status,
                    "callback_trigger_approve": "approve_draft",
                    "callback_trigger_revise": "revise_draft",
                    "callback_trigger_reject": "reject_draft",
                },
            )

            todo_repo = _get_repo()
            await todo_repo.create(todo)
            logger.info(f"Created draft review todo: {todo.id} for task {task_id}")
            return todo

        except Exception as e:
            logger.error(f"Failed to create draft review todo: {e}")
            return None

    async def _broadcast_draft_review(
        self,
        task_id: str,
        agent_id: str,
        risk_score: float,
        trace_id: str,
    ):
        """WS 通知：有新的 Draft 待審核"""
        try:
            from app.agents.ws_manager import get_ws_manager
            mgr = get_ws_manager()
            if mgr:
                await mgr.broadcast({
                    "type": "task_lifecycle",
                    "task_id": task_id,
                    "lifecycle_status": "draft_review",
                    "agent_id": agent_id,
                    "risk_score": risk_score,
                    "trace_id": trace_id,
                    "message": f"{agent_id} 產出待 CEO 審核",
                })
        except Exception as e:
            logger.warning(f"WS broadcast failed: {e}")

    # ================================================================
    # 舊有 Goal Decomposition（向後相容）
    # ================================================================

    async def process_project_request(
        self,
        content: str,
        entities: List[Dict],
        priority: str = "medium",
    ) -> Dict[str, Any]:
        """處理專案需求（舊流程，向後相容）"""
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
            buffer_minutes=int(total_minutes * 0.2),
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
        """分解目標為階段"""
        goal = await self.goals.get(goal_id)
        if not goal:
            raise ValueError(f"Goal {goal_id} not found")

        if not project_type:
            project_type = self._identify_project_type(goal.objective)

        phases = self._decompose_to_phases(goal, project_type)
        goal.phases = phases
        await self.goals.update(goal)

        total_minutes = sum(p.time_estimate.estimated_minutes for p in phases)
        critical_path = [p.name for p in phases]

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
        """取得目標狀態報告"""
        goal = await self.goals.get(goal_id)
        if not goal:
            return {"error": "Goal not found"}

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

        blockers = []
        for phase in goal.phases:
            if phase.status == PhaseStatus.BLOCKED:
                blockers.append({
                    "phase": phase.name,
                    "blockers": phase.blockers,
                })

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
        """處理升級"""
        goal = await self.goals.get(goal_id)
        if not goal:
            return {"error": "Goal not found"}

        if goal.notes:
            goal.notes += f"\n[ESCALATION {datetime.now().isoformat()}] {issue}"
        else:
            goal.notes = f"[ESCALATION {datetime.now().isoformat()}] {issue}"

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
        """重新規劃"""
        goal = await self.goals.get(goal_id)
        if not goal:
            return {"error": "Goal not found"}

        changes = []

        if "add_buffer_minutes" in adjustments:
            extra = adjustments["add_buffer_minutes"]
            goal.time_estimate.buffer_minutes += extra
            changes.append(f"增加 {extra} 分鐘緩衝時間")

        if "extend_phase" in adjustments:
            phase_id = adjustments["extend_phase"]["phase_id"]
            extra_minutes = adjustments["extend_phase"]["minutes"]
            for phase in goal.phases:
                if phase.id == phase_id:
                    phase.time_estimate.estimated_minutes += extra_minutes
                    phase.time_estimate.buffer_minutes += int(extra_minutes * 0.1)
                    changes.append(f"階段 {phase.name} 增加 {extra_minutes} 分鐘")

        note = f"[REPLAN {datetime.now().isoformat()}] {reason}"
        goal.notes = f"{goal.notes}\n{note}" if goal.notes else note

        await self.goals.update(goal)

        return {
            "status": "replanned",
            "changes": changes,
            "new_estimate": goal.time_estimate.to_dict(),
        }

    # ================================================================
    # Private helpers
    # ================================================================

    def _identify_project_type(self, content: str) -> str:
        """識別專案類型"""
        content_lower = content.lower()

        if any(kw in content_lower for kw in ["爬蟲", "crawler", "scraper", "爬取"]):
            return "crawler"
        elif any(kw in content_lower for kw in ["開發", "系統", "功能", "develop", "build"]):
            return "development"
        else:
            return "development"

    def _extract_title(self, content: str) -> str:
        """提取標題"""
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
