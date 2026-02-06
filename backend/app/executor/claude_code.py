"""
Claude Code CLI Executor

透過 Claude Code CLI 執行 Agent 任務，而非直接呼叫 LLM API。
這讓 Agent 能夠：
- 執行終端機指令
- 讀寫檔案
- 進行 Git 操作
- 與外部系統互動
"""

import asyncio
import json
import logging
import os
import subprocess
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class ExecutionResult:
    """Claude Code 執行結果"""
    success: bool
    output: str
    error: Optional[str] = None
    duration_seconds: float = 0.0
    exit_code: int = 0


class ClaudeCodeExecutor:
    """
    Claude Code CLI 執行器

    使用 Claude Code CLI 來執行 Agent 任務，
    而非透過 API 呼叫 LLM。

    使用範例：
        executor = ClaudeCodeExecutor(working_dir="/path/to/project")
        result = await executor.execute("讀取 README.md 並總結內容")
    """

    def __init__(
        self,
        working_dir: str,
        allowed_tools: Optional[List[str]] = None,
        max_turns: int = 10,
        timeout_seconds: int = 300,
    ):
        """
        初始化執行器

        Args:
            working_dir: 工作目錄
            allowed_tools: 允許的工具列表（預設全部允許）
            max_turns: 最大對話輪數
            timeout_seconds: 執行超時秒數
        """
        self.working_dir = working_dir
        self.allowed_tools = allowed_tools
        self.max_turns = max_turns
        self.timeout_seconds = timeout_seconds

        # 確保 Claude Code CLI 可用
        self._verify_cli()

    def _verify_cli(self):
        """驗證 Claude Code CLI 是否可用"""
        try:
            result = subprocess.run(
                ["claude", "--version"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode != 0:
                raise RuntimeError("Claude Code CLI not available")
            logger.info(f"Claude Code CLI version: {result.stdout.strip()}")
        except FileNotFoundError:
            raise RuntimeError(
                "Claude Code CLI not found. Please install it first: "
                "https://docs.anthropic.com/claude-code"
            )

    async def execute(
        self,
        prompt: str,
        context: Optional[Dict[str, Any]] = None,
        output_format: str = "text",
    ) -> ExecutionResult:
        """
        執行 Claude Code 任務

        Args:
            prompt: 任務描述
            context: 額外上下文資訊
            output_format: 輸出格式 ("text" 或 "json")

        Returns:
            ExecutionResult: 執行結果
        """
        # 構建完整 prompt
        full_prompt = self._build_prompt(prompt, context)

        # 構建命令
        cmd = self._build_command(full_prompt, output_format)

        logger.info(f"Executing Claude Code task in {self.working_dir}")
        logger.debug(f"Prompt: {prompt[:100]}...")

        start_time = datetime.now()

        try:
            # 使用 asyncio 執行 subprocess
            result = await asyncio.wait_for(
                self._run_subprocess(cmd),
                timeout=self.timeout_seconds,
            )

            duration = (datetime.now() - start_time).total_seconds()

            return ExecutionResult(
                success=result.returncode == 0,
                output=result.stdout,
                error=result.stderr if result.returncode != 0 else None,
                duration_seconds=duration,
                exit_code=result.returncode,
            )

        except asyncio.TimeoutError:
            duration = (datetime.now() - start_time).total_seconds()
            return ExecutionResult(
                success=False,
                output="",
                error=f"Execution timed out after {self.timeout_seconds} seconds",
                duration_seconds=duration,
                exit_code=-1,
            )

        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds()
            return ExecutionResult(
                success=False,
                output="",
                error=str(e),
                duration_seconds=duration,
                exit_code=-1,
            )

    async def _run_subprocess(self, cmd: List[str]) -> subprocess.CompletedProcess:
        """異步執行 subprocess"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            lambda: subprocess.run(
                cmd,
                cwd=self.working_dir,
                capture_output=True,
                text=True,
            ),
        )

    def _build_prompt(
        self,
        prompt: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """構建完整 prompt"""
        parts = [prompt]

        if context:
            parts.append("\n\n## Context")
            for key, value in context.items():
                if isinstance(value, (dict, list)):
                    parts.append(f"\n### {key}\n```json\n{json.dumps(value, ensure_ascii=False, indent=2)}\n```")
                else:
                    parts.append(f"\n### {key}\n{value}")

        return "\n".join(parts)

    def _build_command(self, prompt: str, output_format: str) -> List[str]:
        """構建 CLI 命令"""
        cmd = [
            "claude",
            "-p", prompt,
            "--max-turns", str(self.max_turns),
        ]

        if output_format == "json":
            cmd.extend(["--output-format", "json"])

        if self.allowed_tools:
            cmd.extend(["--allowedTools", ",".join(self.allowed_tools)])

        return cmd

    async def execute_with_approval(
        self,
        prompt: str,
        approval_callback,
        context: Optional[Dict[str, Any]] = None,
    ) -> ExecutionResult:
        """
        執行需要審批的任務

        當任務需要 CEO 審批時，會呼叫 approval_callback 等待審批

        Args:
            prompt: 任務描述
            approval_callback: 審批回調函數
            context: 額外上下文

        Returns:
            ExecutionResult: 執行結果
        """
        # 第一階段：分析任務是否需要審批
        analysis_prompt = f"""
        分析以下任務是否需要 CEO 審批：

        {prompt}

        如果任務涉及以下情況，請回答 "需要審批" 並說明原因：
        - 折扣超過 10%
        - 金額超過預算
        - 影響公司形象的決策
        - 任何不確定的情況

        否則回答 "可以執行"。
        """

        analysis = await self.execute(analysis_prompt, output_format="text")

        if "需要審批" in analysis.output:
            # 等待審批
            approval = await approval_callback({
                "task": prompt,
                "reason": analysis.output,
                "context": context,
            })

            if not approval.get("approved", False):
                return ExecutionResult(
                    success=False,
                    output="Task rejected by CEO",
                    error=approval.get("feedback", "No feedback provided"),
                )

        # 執行任務
        return await self.execute(prompt, context)


class AgentExecutor:
    """
    Agent 專用執行器

    為特定 Agent 預設 system prompt 和權限
    """

    def __init__(
        self,
        agent_id: str,
        agent_name: str,
        system_prompt: str,
        executor: ClaudeCodeExecutor,
    ):
        self.agent_id = agent_id
        self.agent_name = agent_name
        self.system_prompt = system_prompt
        self.executor = executor

    async def run(
        self,
        task: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> ExecutionResult:
        """執行 Agent 任務"""
        full_prompt = f"""
{self.system_prompt}

---

## 當前任務

{task}

---

請執行上述任務並回報結果。
如果遇到任何需要 CEO 決策的情況，請明確指出並停止執行。
"""

        agent_context = {
            "agent_id": self.agent_id,
            "agent_name": self.agent_name,
            **(context or {}),
        }

        return await self.executor.execute(full_prompt, agent_context)
