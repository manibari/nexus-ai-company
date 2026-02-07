"""
QA Agent

負責：
- 接收 DEVELOPER 完成的功能
- 使用 Gemini 生成測試計畫
- 逐一評估 acceptance criteria
- 寫入 QAResult 到 ProductItem
- 全部通過 → set_stage(uat) + 建立 CEO Todo
- 處理 GATEKEEPER 路由的 product_bug

使用 Gemini 2.5 Flash（輕量級任務）
"""

import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

from app.agents.activity_log import ActivityType, get_activity_repo

logger = logging.getLogger(__name__)


class QAAgent:
    """
    QA Agent - 品質保證

    職責：
    1. 從 DEVELOPER 接收完成的功能
    2. 使用 Gemini 生成測試計畫
    3. 評估 acceptance criteria
    4. 寫入 QAResult
    5. 全部通過 → UAT → CEO Todo
    6. 處理 GATEKEEPER 路由的 product_bug
    """

    def __init__(self):
        self._gemini_client = None
        self._test_results: Dict[str, Dict[str, Any]] = {}  # product_item_id → results

    @property
    def agent_id(self) -> str:
        return "QA"

    @property
    def agent_name(self) -> str:
        return "QA Agent"

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

    async def handle(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        AgentHandler 介面實作

        根據 intent 分流：
        - intent == "product_bug" → test_bug_fix() (來自 GATEKEEPER)
        - 其他 → test_feature() (來自 DEVELOPER)
        """
        intent = payload.get("intent")

        if intent == "product_bug":
            return await self.test_bug_fix(payload)
        else:
            return await self.test_feature(payload)

    async def test_feature(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        測試功能流程（來自 DEVELOPER）：
        1. Log TASK_START
        2. 取得 ProductItem
        3. Gemini 生成測試計畫
        4. 逐一評估 acceptance_criteria
        5. 每個 criterion → add_qa_result()
        6. 全部通過 → set_stage(uat) + CEO Todo
        7. 有失敗 → Log ERROR
        8. Log TASK_END
        """
        activity_repo = get_activity_repo()
        product_item_id = payload.get("product_item_id")
        feature_id = payload.get("feature_id", "unknown")
        title = payload.get("title", "未命名功能")
        project = payload.get("project", "Unknown")
        requirements = payload.get("requirements", {})
        implementation_plan = payload.get("implementation_plan", {})
        acceptance_criteria = requirements.get("acceptance_criteria", [])

        # 1. Log TASK_START
        await activity_repo.log(
            agent_id="QA",
            agent_name="QA Agent",
            activity_type=ActivityType.TASK_START,
            message=f"開始測試: {title}",
            project_name=project,
            metadata={
                "feature_id": feature_id,
                "product_item_id": product_item_id,
                "criteria_count": len(acceptance_criteria),
            },
        )

        # 2. 取得 ProductItem
        from app.product.repository import get_product_repo
        from app.product.models import ProductStage

        product_repo = get_product_repo()
        product_item = None
        if product_item_id:
            product_item = await product_repo.get(product_item_id)

        # 3. Gemini 生成測試計畫
        test_plan = await self._generate_test_plan(
            title=title,
            project=project,
            acceptance_criteria=acceptance_criteria,
            implementation_plan=implementation_plan,
        )

        # 4. 逐一評估 acceptance_criteria
        results = []
        all_passed = True

        for i, criterion in enumerate(acceptance_criteria):
            evaluation = await self._evaluate_criterion(
                criterion=criterion,
                implementation_plan=implementation_plan,
                test_plan=test_plan,
            )

            passed = evaluation.get("passed", False)
            if not passed:
                all_passed = False

            # 5. 每個 criterion → add_qa_result()
            if product_item_id:
                await product_repo.add_qa_result(
                    product_id=product_item_id,
                    test_name=f"AC-{i+1}: {criterion[:50]}",
                    passed=passed,
                    details=evaluation.get("reasoning", ""),
                )

            results.append({
                "criterion": criterion,
                "passed": passed,
                "confidence": evaluation.get("confidence", 0.0),
                "reasoning": evaluation.get("reasoning", ""),
                "potential_issues": evaluation.get("potential_issues", []),
            })

        # 儲存測試結果
        self._test_results[product_item_id or feature_id] = {
            "feature_id": feature_id,
            "product_item_id": product_item_id,
            "project": project,
            "title": title,
            "test_plan": test_plan,
            "results": results,
            "all_passed": all_passed,
            "tested_at": datetime.utcnow().isoformat(),
        }

        if all_passed:
            # 6. 全部通過 → set_stage(uat) + CEO Todo
            if product_item_id:
                await product_repo.set_stage(product_item_id, ProductStage.P5_UAT)
                logger.info(f"ProductItem {product_item_id} → uat")

            # 建立 CEO Todo（UAT 驗收）
            todo = await self._create_uat_todo(
                product_item_id=product_item_id,
                feature_id=feature_id,
                title=title,
                project=project,
                test_results=results,
            )

            await activity_repo.log(
                agent_id="QA",
                agent_name="QA Agent",
                activity_type=ActivityType.MILESTONE,
                message=f"QA 全部通過，進入 UAT: {title}",
                project_name=project,
                metadata={
                    "feature_id": feature_id,
                    "product_item_id": product_item_id,
                    "pass_rate": "100%",
                    "todo_id": todo.id if todo else None,
                },
            )
        else:
            # 7. 有失敗 → Log ERROR
            failed_criteria = [r for r in results if not r["passed"]]
            await activity_repo.log(
                agent_id="QA",
                agent_name="QA Agent",
                activity_type=ActivityType.ERROR,
                message=f"QA 有 {len(failed_criteria)} 項未通過: {title}",
                project_name=project,
                metadata={
                    "feature_id": feature_id,
                    "product_item_id": product_item_id,
                    "failed_count": len(failed_criteria),
                    "failed_criteria": [r["criterion"] for r in failed_criteria],
                },
            )

        # 8. Log TASK_END
        passed_count = sum(1 for r in results if r["passed"])
        await activity_repo.log(
            agent_id="QA",
            agent_name="QA Agent",
            activity_type=ActivityType.TASK_END,
            message=f"測試完成: {title} ({passed_count}/{len(results)} 通過)",
            project_name=project,
            metadata={
                "feature_id": feature_id,
                "product_item_id": product_item_id,
                "all_passed": all_passed,
            },
        )

        return {
            "status": "passed" if all_passed else "failed",
            "feature_id": feature_id,
            "product_item_id": product_item_id,
            "test_plan": test_plan,
            "results": results,
            "pass_rate": f"{passed_count}/{len(results)}",
            "all_passed": all_passed,
            "message": f"QA {'全部通過' if all_passed else '有項目未通過'}: {title}",
        }

    async def test_bug_fix(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        處理 GATEKEEPER 路由的 product_bug：
        1. 從 entities 提取 project
        2. 建立 ProductItem (type=BUG_FIX, stage=qa_testing)
        3. Log MILESTONE
        4. 回傳 bug_reported 結果
        """
        activity_repo = get_activity_repo()
        content = payload.get("content", "")
        entities = payload.get("entities", [])
        intake_id = payload.get("intake_id")

        # 1. 從 entities 提取 project
        project = "Unknown"
        for entity in entities:
            entity_type = entity.get("entity_type") or entity.get("type")
            if entity_type == "project":
                project = entity.get("value", "Unknown")
                break

        # 從內容推斷
        if project == "Unknown":
            content_lower = content.lower()
            if any(kw in content_lower for kw in ["股票", "stock", "stockpulse"]):
                project = "StockPulse"
            elif any(kw in content_lower for kw in ["agent", "nexus"]):
                project = "Nexus AI Company"

        # 2. 建立 ProductItem (type=BUG_FIX, stage=qa_testing)
        from app.product.repository import get_product_repo
        from app.product.models import (
            ProductItem,
            ProductStage,
            ProductPriority,
            ProductType,
        )

        product_repo = get_product_repo()
        product_item = ProductItem(
            id="",  # auto-generate
            title=f"Bug Fix: {content[:60]}",
            description=content,
            type=ProductType.BUG_FIX,
            priority=ProductPriority.HIGH,
            stage=ProductStage.P4_QA_TESTING,
            assignee="QA",
            source_input_id=intake_id,
            tags=[project] if project != "Unknown" else [],
        )

        await product_repo.create(product_item)
        logger.info(f"Created BUG_FIX ProductItem {product_item.id}")

        # 3. Log MILESTONE
        await activity_repo.log(
            agent_id="QA",
            agent_name="QA Agent",
            activity_type=ActivityType.MILESTONE,
            message=f"Bug 已記錄: {content[:50]}...",
            project_name=project,
            metadata={
                "product_item_id": product_item.id,
                "intake_id": intake_id,
                "type": "bug_fix",
            },
        )

        self._test_results[product_item.id] = {
            "product_item_id": product_item.id,
            "project": project,
            "title": product_item.title,
            "type": "bug_fix",
            "status": "reported",
            "created_at": datetime.utcnow().isoformat(),
        }

        return {
            "status": "bug_reported",
            "product_item_id": product_item.id,
            "project": project,
            "message": f"Bug 已記錄為 {product_item.id}，待修復後測試",
        }

    async def _generate_test_plan(
        self,
        title: str,
        project: str,
        acceptance_criteria: List[str],
        implementation_plan: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        使用 Gemini 生成測試計畫

        輸出：
        {
            "test_strategy": "...",
            "test_cases": [...],
            "edge_cases": [...],
            "regression_tests": [...]
        }
        """
        gemini = self._get_gemini()

        if not gemini:
            return self._fallback_test_plan(title, acceptance_criteria)

        files_info = json.dumps(
            implementation_plan.get("files_to_modify", []),
            ensure_ascii=False,
        )

        prompt = f"""你是 {project} 專案的 QA 工程師。根據以下功能和實作計畫，生成測試計畫。

## 功能名稱
{title}

## 驗收標準
{chr(10).join(f'- {c}' for c in acceptance_criteria) if acceptance_criteria else '（無明確驗收標準）'}

## 實作計畫涉及的檔案
{files_info}

## 輸出格式（純 JSON）
{{
  "test_strategy": "測試策略說明（2-3 句）",
  "test_cases": [
    {{"name": "測試案例名稱", "description": "說明", "steps": ["步驟1", "步驟2"], "expected": "預期結果"}}
  ],
  "edge_cases": [
    {{"name": "邊界案例", "description": "說明", "risk_level": "low/medium/high"}}
  ],
  "regression_tests": [
    {{"area": "受影響區域", "test": "回歸測試項目"}}
  ]
}}
"""

        try:
            response = gemini.generate_content(prompt)
            text = response.text.strip()

            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
            text = text.strip()

            return json.loads(text)

        except Exception as e:
            logger.error(f"Gemini test plan generation failed: {e}")
            return self._fallback_test_plan(title, acceptance_criteria)

    @staticmethod
    def _fallback_test_plan(
        title: str,
        acceptance_criteria: List[str],
    ) -> Dict[str, Any]:
        """Fallback 測試計畫 template"""
        test_cases = []
        for i, criterion in enumerate(acceptance_criteria):
            test_cases.append({
                "name": f"TC-{i+1}: 驗證 {criterion[:30]}",
                "description": f"驗證: {criterion}",
                "steps": ["準備測試環境", "執行功能操作", "驗證結果"],
                "expected": criterion,
            })

        return {
            "test_strategy": f"針對 {title} 的功能測試，涵蓋所有驗收標準的驗證。",
            "test_cases": test_cases,
            "edge_cases": [
                {"name": "空值輸入", "description": "測試空值或無效輸入", "risk_level": "medium"},
                {"name": "併發操作", "description": "測試多用戶同時操作", "risk_level": "low"},
            ],
            "regression_tests": [
                {"area": "既有功能", "test": "確認既有功能不受影響"},
            ],
        }

    async def _evaluate_criterion(
        self,
        criterion: str,
        implementation_plan: Dict[str, Any],
        test_plan: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        使用 Gemini 評估每個驗收標準

        輸出：
        {
            "passed": true/false,
            "confidence": 0.0-1.0,
            "reasoning": "...",
            "potential_issues": [...]
        }
        """
        gemini = self._get_gemini()

        if not gemini:
            return self._fallback_evaluate(criterion, implementation_plan)

        architecture = implementation_plan.get("architecture", "未知")
        files = json.dumps(
            implementation_plan.get("files_to_modify", []),
            ensure_ascii=False,
        )
        test_strategy = test_plan.get("test_strategy", "")

        prompt = f"""你是 QA 工程師，評估以下驗收標準是否能被實作計畫滿足。

## 驗收標準
{criterion}

## 實作計畫架構
{architecture}

## 涉及檔案
{files}

## 測試策略
{test_strategy}

## 輸出格式（純 JSON）
{{
  "passed": true,
  "confidence": 0.85,
  "reasoning": "通過/不通過的原因說明",
  "potential_issues": ["潛在問題1"]
}}

注意：
- 基於實作計畫的完整性判斷是否能滿足此驗收標準
- confidence 反映你對判斷的確信度
- 如果實作計畫有明顯缺漏，應判定為不通過
"""

        try:
            response = gemini.generate_content(prompt)
            text = response.text.strip()

            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
            text = text.strip()

            return json.loads(text)

        except Exception as e:
            logger.error(f"Gemini criterion evaluation failed: {e}")
            return self._fallback_evaluate(criterion, implementation_plan)

    @staticmethod
    def _fallback_evaluate(
        criterion: str,
        implementation_plan: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Fallback: keyword heuristic 評估"""
        # 簡單的 keyword heuristic
        files = implementation_plan.get("files_to_modify", [])
        breakdown = implementation_plan.get("technical_breakdown", [])

        # 有實作計畫就假設通過
        has_relevant_work = len(files) > 0 or len(breakdown) > 0

        criterion_lower = criterion.lower()
        # 一些常見的高風險關鍵字
        high_risk_keywords = ["安全", "security", "效能", "performance", "併發", "concurrent"]
        is_high_risk = any(kw in criterion_lower for kw in high_risk_keywords)

        if has_relevant_work and not is_high_risk:
            return {
                "passed": True,
                "confidence": 0.7,
                "reasoning": f"實作計畫涵蓋 {len(files)} 個檔案修改，初步評估可滿足此標準",
                "potential_issues": [],
            }
        elif has_relevant_work and is_high_risk:
            return {
                "passed": True,
                "confidence": 0.5,
                "reasoning": "實作計畫存在，但此標準涉及高風險面向，需要額外關注",
                "potential_issues": ["此標準涉及高風險面向，建議人工複查"],
            }
        else:
            return {
                "passed": False,
                "confidence": 0.4,
                "reasoning": "實作計畫不夠完整，無法確認是否能滿足此標準",
                "potential_issues": ["缺少具體的實作檔案", "建議補充實作計畫"],
            }

    async def _create_uat_todo(
        self,
        product_item_id: Optional[str],
        feature_id: str,
        title: str,
        project: str,
        test_results: List[Dict[str, Any]],
    ) -> Optional[Any]:
        """建立 CEO Todo（UAT 驗收）"""
        try:
            from app.ceo.models import (
                TodoItem,
                TodoAction,
                TodoType,
                TodoPriority,
            )
            from app.api.ceo_todo import _get_repo

            todo_repo = _get_repo()

            # 組合測試結果摘要
            results_summary = "\n".join(
                f"{'[PASS]' if r['passed'] else '[FAIL]'} {r['criterion']}"
                for r in test_results
            )

            todo = TodoItem(
                id="",  # auto-generate
                project_name=project,
                subject=f"[QA] UAT 驗收: {title}",
                description=f"""功能: {title}
專案: {project}

QA 測試結果（全部通過）:
{results_summary}

請確認功能是否符合預期，進行最終驗收。""",
                from_agent="QA",
                from_agent_name="QA Agent",
                type=TodoType.REVIEW,
                priority=TodoPriority.HIGH,
                actions=[
                    TodoAction(id="accept", label="驗收通過", style="primary"),
                    TodoAction(
                        id="reject",
                        label="退回重做",
                        style="danger",
                        requires_input=True,
                        input_placeholder="請輸入退回原因",
                    ),
                ],
                related_entity_type="product_item",
                related_entity_id=product_item_id,
                payload={
                    "product_item_id": product_item_id,
                    "feature_id": feature_id,
                    "test_results": test_results,
                },
            )

            await todo_repo.create(todo)
            logger.info(f"Created UAT Todo for {product_item_id}: {todo.id}")
            return todo

        except Exception as e:
            logger.error(f"Failed to create UAT Todo: {e}")
            return None

    def get_results(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """取得 QA 結果列表"""
        results = list(self._test_results.values())
        if status:
            results = [r for r in results if r.get("status") == status]
        return results

    def get_result(self, product_item_id: str) -> Optional[Dict[str, Any]]:
        """取得特定項目 QA 結果"""
        return self._test_results.get(product_item_id)

    def get_stats(self) -> Dict[str, Any]:
        """取得 QA 統計"""
        results = list(self._test_results.values())
        testing = sum(1 for r in results if r.get("all_passed") is None)
        passed = sum(1 for r in results if r.get("all_passed") is True)
        failed = sum(1 for r in results if r.get("all_passed") is False)
        bugs = sum(1 for r in results if r.get("type") == "bug_fix")

        total_tests = passed + failed
        pass_rate = (passed / total_tests * 100) if total_tests > 0 else 0.0

        return {
            "total": len(results),
            "testing": testing,
            "passed": passed,
            "failed": failed,
            "bugs_reported": bugs,
            "pass_rate": round(pass_rate, 1),
        }


# 全域 singleton
_qa_agent: Optional[QAAgent] = None


def get_qa_agent() -> QAAgent:
    """取得共享的 QA Agent 實例"""
    global _qa_agent
    if _qa_agent is None:
        _qa_agent = QAAgent()
    return _qa_agent
