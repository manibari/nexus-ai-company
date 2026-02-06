# ADR-003: 使用 Claude Code CLI 作為 Agent 執行引擎

> **狀態**: 已採納
> **日期**: 2026-02-06
> **決策者**: CEO

---

## 背景

在 ADR-001 和 ADR-002 中，我們規劃透過 LLM API（Gemini/Claude/OpenAI）來驅動 Agent 思考。
經過進一步討論，決定採用更直接的方式：**使用 Claude Code CLI 作為 Agent 執行引擎**。

## 決策

**每個 Agent 使用 Claude Code CLI 執行任務**

而非：
```python
# 舊方案：透過 API 呼叫
response = await claude_api.chat(messages)
```

改為：
```python
# 新方案：透過 Claude Code CLI 執行
result = subprocess.run(["claude", "-p", prompt, "--output-format", "json"])
```

## 架構變更

### Before (API 驅動)

```
┌─────────────┐     API Call     ┌─────────────┐
│   Agent     │ ───────────────▶ │  Claude API │
│  (Python)   │ ◀─────────────── │             │
└─────────────┘     Response     └─────────────┘
```

### After (CLI 驅動)

```
┌─────────────┐    subprocess    ┌─────────────┐
│   Agent     │ ───────────────▶ │ Claude Code │
│ Orchestrator│                  │    CLI      │
└─────────────┘                  └──────┬──────┘
                                        │
                                        │ 可執行
                                        ▼
                               ┌─────────────────┐
                               │  - 讀寫檔案      │
                               │  - 執行指令      │
                               │  - Git 操作     │
                               │  - 網路請求      │
                               └─────────────────┘
```

## 優點

1. **完整工具鏈**
   - Claude Code 已經整合檔案操作、Git、終端機等工具
   - 不需要自己實作 function calling

2. **自主執行能力**
   - Agent 可以直接執行 bash 指令
   - 可以讀寫檔案、創建專案
   - 可以進行網路操作

3. **開發一致性**
   - 使用相同的工具開發和執行
   - 減少 API 整合的複雜度

4. **成本模式**
   - 使用 Claude Code 的計費模式
   - 可能與 API 計費不同，需確認

## 實作方式

### Agent 執行器

```python
import subprocess
import json

class ClaudeCodeExecutor:
    """透過 Claude Code CLI 執行 Agent 任務"""

    def __init__(self, working_dir: str):
        self.working_dir = working_dir

    async def execute(
        self,
        prompt: str,
        allowed_tools: list[str] = None,
        max_turns: int = 10
    ) -> dict:
        """
        執行 Claude Code 任務

        Args:
            prompt: 任務描述
            allowed_tools: 允許的工具列表
            max_turns: 最大對話輪數

        Returns:
            執行結果
        """
        cmd = [
            "claude",
            "-p", prompt,
            "--output-format", "json",
            "--max-turns", str(max_turns),
        ]

        if allowed_tools:
            cmd.extend(["--allowedTools", ",".join(allowed_tools)])

        result = subprocess.run(
            cmd,
            cwd=self.working_dir,
            capture_output=True,
            text=True
        )

        return json.loads(result.stdout)
```

### Agent 定義

```python
class SalesAgent:
    """Sales Agent - 使用 Claude Code 執行"""

    def __init__(self, executor: ClaudeCodeExecutor):
        self.executor = executor
        self.system_prompt = """
        你是 Nexus AI Company 的 Sales Agent (代號: HUNTER)。
        你的職責是：
        1. 開發潛在客戶
        2. 發送開發信
        3. 追蹤客戶回覆
        4. 當需要 CEO 決策時（如折扣 > 10%），停止並請求審批
        """

    async def run_task(self, task: dict) -> dict:
        prompt = f"""
        {self.system_prompt}

        當前任務：
        {json.dumps(task, ensure_ascii=False, indent=2)}

        請執行此任務並回報結果。
        """

        return await self.executor.execute(prompt)
```

## 與 Human-in-the-Loop 整合

當 Agent 需要 CEO 審批時：

```python
# Agent 透過 Claude Code 執行任務
# 當遇到需要審批的情況...

result = await executor.execute("""
    客戶要求 15% 折扣，這超出我的授權範圍。
    請將此請求保存到 inbox，等待 CEO 決策。

    執行步驟：
    1. 讀取 inbox.json
    2. 新增待審批項目
    3. 保存檔案
    4. 回傳 BLOCKED_USER 狀態
""")
```

## 風險與考量

1. **執行隔離**
   - Claude Code 有完整的檔案系統存取權
   - 需要限制 Agent 可存取的目錄

2. **並發控制**
   - 多個 Agent 同時執行可能衝突
   - 需要任務佇列或鎖機制

3. **錯誤處理**
   - Claude Code 可能執行失敗
   - 需要重試和回滾機制

4. **計費追蹤**
   - 需要解析 Claude Code 的使用量
   - 可能需要額外的監控

## 下一步

1. 建立 `ClaudeCodeExecutor` 類別
2. 為每個 Agent 定義專屬的 system prompt
3. 設計任務佇列機制
4. 實作執行結果解析

---

## 參考文件

- [ADR-001-tech-stack.md](./ADR-001-tech-stack.md)
- [ADR-002-llm-priority.md](./ADR-002-llm-priority.md)
- [003-agent-communication.md](../architecture/003-agent-communication.md)
