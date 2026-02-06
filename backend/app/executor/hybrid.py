"""
Hybrid Executor: Gemini (L1) + Claude Code (L2)

L1 (Gemini API): 日常對話、指令理解、簡單分析
L2 (Claude Code CLI): 複雜任務執行、程式開發、資料查詢
"""

import json
import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional

from app.executor.claude_code import ClaudeCodeExecutor, ExecutionResult
from app.llm import LLMProviderFactory, Message

logger = logging.getLogger(__name__)


class ExecutionLevel(Enum):
    """執行層級"""
    L1_SIMPLE = "l1_gemini"      # 簡單任務 - Gemini API
    L2_COMPLEX = "l2_claude"    # 複雜任務 - Claude Code CLI


@dataclass
class TaskAnalysis:
    """任務分析結果"""
    level: ExecutionLevel
    requires_execution: bool
    execution_prompt: Optional[str] = None
    direct_response: Optional[str] = None
    context: Optional[Dict[str, Any]] = None
    reasoning: str = ""


TASK_ANALYZER_PROMPT = '''
你是 Nexus AI Company 的任務分析器。
分析用戶或系統發來的指令，決定最佳的處理方式。

## 判斷標準

需要 Claude Code 執行 (L2) 的任務：
- 讀取或寫入檔案
- 執行程式碼或腳本
- 查詢資料庫或外部 API
- Git 操作（commit, push, pull）
- 網頁爬蟲或資料抓取
- 建立或修改專案結構
- 執行測試
- 任何需要存取檔案系統或網路的操作

可直接回應 (L1) 的任務：
- 簡單問答
- 狀態查詢（查詢記憶體中的資料）
- 分析文字內容
- 提供建議或解釋
- 閒聊

## 輸出格式

請以 JSON 格式回應：
```json
{
    "requires_execution": true/false,
    "execution_prompt": "給 Claude Code 的詳細指令（如果 requires_execution=true）",
    "direct_response": "直接回應內容（如果 requires_execution=false）",
    "context": {},
    "reasoning": "你的判斷理由"
}
```
'''


class HybridExecutor:
    """
    混合執行器

    根據任務複雜度自動選擇：
    - L1 (Gemini): 日常對話、簡單分析
    - L2 (Claude Code): 程式開發、資料查詢、檔案操作
    """

    def __init__(
        self,
        claude_executor: ClaudeCodeExecutor,
        gemini_provider=None,
    ):
        """
        初始化混合執行器

        Args:
            claude_executor: Claude Code CLI 執行器
            gemini_provider: Gemini API Provider（如果沒提供會自動建立）
        """
        self.claude = claude_executor

        # 建立 Gemini provider 用於 L1 任務
        if gemini_provider:
            self.gemini = gemini_provider
        else:
            try:
                self.gemini = LLMProviderFactory.create("gemini")
            except ValueError:
                logger.warning("Gemini API not available, will use Claude Code for all tasks")
                self.gemini = None

    async def process(
        self,
        task: str,
        context: Optional[Dict[str, Any]] = None,
        force_level: Optional[ExecutionLevel] = None,
    ) -> Dict[str, Any]:
        """
        處理任務

        Args:
            task: 任務描述
            context: 額外上下文
            force_level: 強制使用特定層級（跳過分析）

        Returns:
            執行結果
        """
        # 如果強制指定層級，直接執行
        if force_level:
            if force_level == ExecutionLevel.L1_SIMPLE:
                return await self._execute_l1(task, context)
            else:
                return await self._execute_l2(task, context)

        # 如果沒有 Gemini，直接用 Claude Code
        if not self.gemini:
            logger.info("No Gemini available, using Claude Code for all tasks")
            return await self._execute_l2(task, context)

        # 分析任務
        analysis = await self._analyze_task(task, context)

        # 根據分析結果執行
        if analysis.requires_execution:
            logger.info(f"Task requires L2 execution: {analysis.reasoning}")
            return await self._execute_l2(
                analysis.execution_prompt or task,
                analysis.context or context,
            )
        else:
            logger.info(f"Task handled by L1: {analysis.reasoning}")
            return {
                "success": True,
                "response": analysis.direct_response,
                "level": ExecutionLevel.L1_SIMPLE.value,
                "reasoning": analysis.reasoning,
            }

    async def _analyze_task(
        self,
        task: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> TaskAnalysis:
        """使用 Gemini 分析任務"""
        user_message = f"""
任務：{task}

上下文：{json.dumps(context, ensure_ascii=False) if context else '無'}

請分析這個任務應該如何處理。
"""

        try:
            response = await self.gemini.chat([
                Message(role="system", content=TASK_ANALYZER_PROMPT),
                Message(role="user", content=user_message),
            ])

            # 解析 JSON 回應
            return self._parse_analysis(response.content)

        except Exception as e:
            logger.error(f"Task analysis failed: {e}")
            # 預設使用 L2
            return TaskAnalysis(
                level=ExecutionLevel.L2_COMPLEX,
                requires_execution=True,
                execution_prompt=task,
                context=context,
                reasoning=f"Analysis failed, defaulting to L2: {e}",
            )

    def _parse_analysis(self, response: str) -> TaskAnalysis:
        """解析分析結果"""
        try:
            # 處理可能包含 markdown code block 的情況
            if "```json" in response:
                response = response.split("```json")[1].split("```")[0]
            elif "```" in response:
                response = response.split("```")[1].split("```")[0]

            data = json.loads(response.strip())

            requires_execution = data.get("requires_execution", False)

            return TaskAnalysis(
                level=ExecutionLevel.L2_COMPLEX if requires_execution else ExecutionLevel.L1_SIMPLE,
                requires_execution=requires_execution,
                execution_prompt=data.get("execution_prompt"),
                direct_response=data.get("direct_response"),
                context=data.get("context"),
                reasoning=data.get("reasoning", ""),
            )

        except json.JSONDecodeError:
            logger.warning("Failed to parse analysis as JSON, defaulting to L2")
            return TaskAnalysis(
                level=ExecutionLevel.L2_COMPLEX,
                requires_execution=True,
                reasoning="JSON parse failed",
            )

    async def _execute_l1(
        self,
        task: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """執行 L1 任務 (Gemini)"""
        if not self.gemini:
            return await self._execute_l2(task, context)

        response = await self.gemini.chat([
            Message(role="user", content=task),
        ])

        return {
            "success": True,
            "response": response.content,
            "level": ExecutionLevel.L1_SIMPLE.value,
            "tokens": {
                "input": response.input_tokens,
                "output": response.output_tokens,
            },
            "cost_usd": response.cost_usd,
        }

    async def _execute_l2(
        self,
        task: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """執行 L2 任務 (Claude Code)"""
        result: ExecutionResult = await self.claude.execute(task, context)

        return {
            "success": result.success,
            "response": result.output,
            "error": result.error,
            "level": ExecutionLevel.L2_COMPLEX.value,
            "duration_seconds": result.duration_seconds,
        }


class AgentHybridExecutor(HybridExecutor):
    """
    Agent 專用混合執行器

    為特定 Agent 預設 system prompt 和行為
    """

    def __init__(
        self,
        agent_id: str,
        agent_name: str,
        agent_prompt: str,
        claude_executor: ClaudeCodeExecutor,
        gemini_provider=None,
    ):
        super().__init__(claude_executor, gemini_provider)
        self.agent_id = agent_id
        self.agent_name = agent_name
        self.agent_prompt = agent_prompt

    async def run_task(
        self,
        task: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """執行 Agent 任務"""
        full_task = f"""
[{self.agent_name} ({self.agent_id})]

{self.agent_prompt}

---

當前任務：
{task}

---

請執行上述任務。如需要 CEO 審批，請明確指出。
"""

        return await self.process(full_task, context)
