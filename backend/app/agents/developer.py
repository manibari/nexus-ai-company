"""
Developer Agent

負責：
- 接收 PM 批准後的功能需求
- 使用 Gemini 生成實作計畫（architecture, files_to_modify, code_snippets）
- 模擬開發流程（不實際執行程式碼）
- 完成後 dispatch 給 QA Agent

使用 Gemini 2.5 Flash（輕量級任務）
"""

import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

from app.agents.activity_log import ActivityType, get_activity_repo

logger = logging.getLogger(__name__)


class DeveloperAgent:
    """
    Developer Agent - 開發者

    職責：
    1. 從 PM 接收批准的功能需求
    2. 使用 Gemini 生成實作計畫
    3. 更新 ProductItem 階段 (in_progress → qa_testing)
    4. 完成後 dispatch 給 QA Agent
    """

    def __init__(self):
        self._gemini_client = None
        self._tasks: Dict[str, Dict[str, Any]] = {}  # product_item_id → task info

    @property
    def agent_id(self) -> str:
        return "DEVELOPER"

    @property
    def agent_name(self) -> str:
        return "Developer Agent"

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

        payload 來自 PM:
        {
            "content": "feature description",
            "feature_id": "FEAT-XXXX",
            "product_item_id": "PROD-2026-XXXX",
            "project": "StockPulse",
            "title": "feature title",
            "requirements": {
                "technical": [...],
                "ui": [...],
                "acceptance_criteria": [...]
            },
            "priority": "p2_medium",
            "estimated_days": 3,
        }
        """
        return await self.develop_feature(payload)

    async def develop_feature(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        開發功能流程：
        1. Log TASK_START
        2. 取得 ProductItem，set_stage → in_progress
        3. Gemini 生成實作計畫
        4. Log MILESTONE（計畫已生成）
        5. set_stage → qa_testing
        6. registry.dispatch("QA", ...) from_agent="DEVELOPER"
        7. Log TASK_END
        """
        activity_repo = get_activity_repo()
        product_item_id = payload.get("product_item_id")
        feature_id = payload.get("feature_id", "unknown")
        title = payload.get("title", "未命名功能")
        project = payload.get("project", "Unknown")
        requirements = payload.get("requirements", {})

        # 1. Log TASK_START
        await activity_repo.log(
            agent_id="DEVELOPER",
            agent_name="Developer Agent",
            activity_type=ActivityType.TASK_START,
            message=f"開始開發: {title}",
            project_name=project,
            metadata={
                "feature_id": feature_id,
                "product_item_id": product_item_id,
                "priority": payload.get("priority"),
            },
        )

        # 2. 取得 ProductItem，set_stage → in_progress
        from app.product.repository import get_product_repo
        from app.product.models import ProductStage

        product_repo = get_product_repo()
        product_item = None
        if product_item_id:
            product_item = await product_repo.set_stage(
                product_item_id, ProductStage.P3_IN_PROGRESS
            )
            if product_item:
                logger.info(f"ProductItem {product_item_id} → in_progress")
            else:
                logger.warning(f"ProductItem {product_item_id} not found or cannot advance")

        # 3. Gemini 生成實作計畫
        implementation_plan = await self._generate_implementation_plan(
            title=title,
            project=project,
            requirements=requirements,
        )

        # 儲存任務資訊
        self._tasks[product_item_id or feature_id] = {
            "feature_id": feature_id,
            "product_item_id": product_item_id,
            "project": project,
            "title": title,
            "status": "developing",
            "implementation_plan": implementation_plan,
            "started_at": datetime.utcnow().isoformat(),
        }

        # 4. Log MILESTONE（計畫已生成）
        await activity_repo.log(
            agent_id="DEVELOPER",
            agent_name="Developer Agent",
            activity_type=ActivityType.MILESTONE,
            message=f"實作計畫已生成: {title}",
            project_name=project,
            metadata={
                "feature_id": feature_id,
                "product_item_id": product_item_id,
                "files_count": len(implementation_plan.get("files_to_modify", [])),
                "complexity": implementation_plan.get("estimated_complexity", "medium"),
            },
        )

        # 5. set_stage → qa_testing
        if product_item_id:
            product_item = await product_repo.set_stage(
                product_item_id, ProductStage.P4_QA_TESTING
            )
            if product_item:
                logger.info(f"ProductItem {product_item_id} → qa_testing")

        # 6. dispatch 給 QA
        qa_dispatch_result = None
        try:
            from app.agents.registry import get_registry
            registry = get_registry()
            qa_dispatch_result = await registry.dispatch(
                target_id="QA",
                payload={
                    "content": payload.get("content", ""),
                    "feature_id": feature_id,
                    "product_item_id": product_item_id,
                    "project": project,
                    "title": title,
                    "requirements": requirements,
                    "implementation_plan": implementation_plan,
                    "priority": payload.get("priority"),
                    "estimated_days": payload.get("estimated_days"),
                },
                from_agent="DEVELOPER",
            )
        except Exception as e:
            logger.error(f"Failed to dispatch to QA: {e}")
            qa_dispatch_result = {"status": "error", "message": str(e)}

        # 更新任務狀態
        task_key = product_item_id or feature_id
        if task_key in self._tasks:
            self._tasks[task_key]["status"] = "qa_dispatched"
            self._tasks[task_key]["completed_at"] = datetime.utcnow().isoformat()

        # 7. Log TASK_END
        await activity_repo.log(
            agent_id="DEVELOPER",
            agent_name="Developer Agent",
            activity_type=ActivityType.TASK_END,
            message=f"開發完成，已提交 QA: {title}",
            project_name=project,
            metadata={
                "feature_id": feature_id,
                "product_item_id": product_item_id,
                "qa_dispatch_status": qa_dispatch_result.get("status") if qa_dispatch_result else None,
            },
        )

        return {
            "status": "completed",
            "feature_id": feature_id,
            "product_item_id": product_item_id,
            "implementation_plan": implementation_plan,
            "qa_dispatch": qa_dispatch_result,
            "message": f"開發完成: {title}，已提交 QA 測試",
        }

    async def _generate_implementation_plan(
        self,
        title: str,
        project: str,
        requirements: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        使用 Gemini 生成實作計畫

        輸出：
        {
            "architecture": "...",
            "files_to_modify": [...],
            "technical_breakdown": [...],
            "code_snippets": [...],
            "dependencies": [...],
            "estimated_complexity": "low/medium/high",
            "risk_factors": [...]
        }
        """
        gemini = self._get_gemini()

        technical = requirements.get("technical", [])
        ui = requirements.get("ui", [])
        acceptance_criteria = requirements.get("acceptance_criteria", [])

        if not gemini:
            # Fallback: 固定 template
            return self._fallback_plan(title, project, technical, ui, acceptance_criteria)

        prompt = f"""你是 {project} 專案的資深開發者。根據以下功能需求，生成實作計畫。

## 功能名稱
{title}

## 技術需求
{chr(10).join(f'- {r}' for r in technical) if technical else '（無明確技術需求）'}

## UI 需求
{chr(10).join(f'- {r}' for r in ui) if ui else '（無明確 UI 需求）'}

## 驗收標準
{chr(10).join(f'- {c}' for c in acceptance_criteria) if acceptance_criteria else '（無明確驗收標準）'}

## 輸出格式（純 JSON）
{{
  "architecture": "架構說明（2-3 句）",
  "files_to_modify": [
    {{"path": "src/...", "action": "create/modify", "description": "說明"}}
  ],
  "technical_breakdown": [
    {{"task": "子任務名稱", "description": "說明", "estimated_hours": 2}}
  ],
  "code_snippets": [
    {{"file": "src/...", "language": "python/typescript", "description": "說明", "code": "程式碼片段"}}
  ],
  "dependencies": ["需要安裝的套件"],
  "estimated_complexity": "low/medium/high",
  "risk_factors": ["潛在風險"]
}}

注意：
1. 按照 {project} 的技術棧規劃
2. 程式碼片段要具體可執行
3. 風險評估要務實
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

            return json.loads(text)

        except Exception as e:
            logger.error(f"Gemini implementation plan generation failed: {e}")
            return self._fallback_plan(title, project, technical, ui, acceptance_criteria)

    @staticmethod
    def _fallback_plan(
        title: str,
        project: str,
        technical: List[str],
        ui: List[str],
        acceptance_criteria: List[str],
    ) -> Dict[str, Any]:
        """Fallback 實作計畫 template"""
        files = []
        if technical:
            files.append({
                "path": "backend/app/api/new_feature.py",
                "action": "create",
                "description": "新功能 API 端點",
            })
            files.append({
                "path": "backend/app/models/new_feature.py",
                "action": "create",
                "description": "資料模型",
            })
        if ui:
            files.append({
                "path": "frontend/src/components/NewFeature.tsx",
                "action": "create",
                "description": "前端元件",
            })

        breakdown = []
        for i, req in enumerate(technical[:3]):
            breakdown.append({
                "task": f"後端實作 #{i+1}",
                "description": req,
                "estimated_hours": 2,
            })
        for i, req in enumerate(ui[:2]):
            breakdown.append({
                "task": f"前端實作 #{i+1}",
                "description": req,
                "estimated_hours": 3,
            })

        return {
            "architecture": f"{project} 使用前後端分離架構，後端 FastAPI + 前端 React，本次新增功能涉及 API 端點與前端元件。",
            "files_to_modify": files or [{"path": "backend/app/api/feature.py", "action": "modify", "description": "功能修改"}],
            "technical_breakdown": breakdown or [{"task": "實作功能", "description": title, "estimated_hours": 4}],
            "code_snippets": [],
            "dependencies": [],
            "estimated_complexity": "medium",
            "risk_factors": ["需要確認與既有功能的整合"],
        }

    def get_tasks(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """取得開發任務列表"""
        tasks = list(self._tasks.values())
        if status:
            tasks = [t for t in tasks if t.get("status") == status]
        return tasks

    def get_task(self, product_item_id: str) -> Optional[Dict[str, Any]]:
        """取得特定任務"""
        return self._tasks.get(product_item_id)

    def get_stats(self) -> Dict[str, Any]:
        """取得開發統計"""
        tasks = list(self._tasks.values())
        in_progress = sum(1 for t in tasks if t.get("status") == "developing")
        completed = sum(1 for t in tasks if t.get("status") in ("qa_dispatched", "completed"))
        return {
            "total": len(tasks),
            "in_progress": in_progress,
            "completed": completed,
        }


# 全域 singleton
_developer_agent: Optional[DeveloperAgent] = None


def get_developer_agent() -> DeveloperAgent:
    """取得共享的 Developer Agent 實例"""
    global _developer_agent
    if _developer_agent is None:
        _developer_agent = DeveloperAgent()
    return _developer_agent
