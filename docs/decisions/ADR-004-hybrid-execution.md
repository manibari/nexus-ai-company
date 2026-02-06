# ADR-004: 混合執行架構 (Gemini + Claude Code)

> **狀態**: 已採納
> **日期**: 2026-02-06
> **決策者**: CEO

---

## 背景

經過 ADR-003 的討論，進一步明確了 AI Agent 的執行策略：
- 不是單一使用 Claude Code CLI
- 而是根據任務類型選擇最適合的執行方式

## 決策

**採用混合執行架構**

### 層級分工

| 層級 | 執行方式 | 使用場景 | 成本 |
|------|----------|----------|------|
| L1: 日常對話 | Gemini API | 指令解析、閒聊、簡單分析 | 低 |
| L2: 複雜任務 | Claude Code CLI | 程式開發、資料查詢、檔案操作 | 高 |

### 執行流程

```
用戶/系統 發出指令
        │
        ▼
┌───────────────────┐
│  Gemini (L1)      │
│  - 理解意圖        │
│  - 判斷複雜度      │
│  - 回應簡單問題    │
└─────────┬─────────┘
          │
    需要執行複雜任務？
          │
    ┌─────┴─────┐
    │           │
   否           是
    │           │
    ▼           ▼
 直接回應   ┌───────────────────┐
           │  Claude Code (L2)  │
           │  - 讀寫檔案         │
           │  - 執行程式碼        │
           │  - Git 操作         │
           │  - 網路查詢         │
           └───────────────────┘
```

## 任務分類規則

### L1 任務 (Gemini API)

- 解析用戶指令
- 狀態查詢（「目前有多少 lead？」）
- 簡單分析（「這封 email 語氣如何？」）
- 閒聊或問答
- 判斷是否需要升級到 L2

### L2 任務 (Claude Code CLI)

- 程式碼撰寫與修改
- 檔案讀取與分析
- 資料庫查詢
- 網頁爬蟲
- Git commit/push
- 執行測試
- 任何需要系統操作的任務

## 實作範例

```python
class HybridExecutor:
    """混合執行器"""

    def __init__(self, gemini_provider, claude_executor):
        self.gemini = gemini_provider
        self.claude = claude_executor

    async def process(self, task: str) -> dict:
        # Step 1: 用 Gemini 分析任務
        analysis = await self.gemini.chat([
            Message(role="system", content=TASK_ANALYZER_PROMPT),
            Message(role="user", content=task)
        ])

        task_info = self._parse_analysis(analysis.content)

        # Step 2: 根據複雜度選擇執行方式
        if task_info["requires_execution"]:
            # L2: 使用 Claude Code CLI
            return await self.claude.execute(
                prompt=task_info["execution_prompt"],
                context=task_info["context"]
            )
        else:
            # L1: 直接用 Gemini 回應
            return {
                "response": task_info["direct_response"],
                "executor": "gemini"
            }


TASK_ANALYZER_PROMPT = '''
你是任務分析器。分析用戶的指令並決定處理方式。

如果任務需要以下操作，設定 requires_execution = true：
- 讀取或寫入檔案
- 執行程式碼
- 查詢資料庫或外部 API
- Git 操作
- 任何系統層級操作

否則，直接提供回應。

回傳 JSON 格式：
{
    "requires_execution": true/false,
    "execution_prompt": "給 Claude Code 的指令（如需要）",
    "direct_response": "直接回應（如不需要執行）",
    "context": {}
}
'''
```

## 成本效益

| 任務類型 | 日均次數 (預估) | 執行方式 | 成本預估 |
|----------|-----------------|----------|----------|
| 狀態查詢 | 50 | Gemini | $0.05 |
| 指令解析 | 100 | Gemini | $0.10 |
| 程式開發 | 10 | Claude Code | $2.00 |
| 資料查詢 | 20 | Claude Code | $1.00 |
| **日總計** | 180 | - | **$3.15** |

## Agent 層級對應

| Agent | L1 任務 | L2 任務 |
|-------|---------|---------|
| Sales | 分析客戶回覆語氣 | 發送開發信、爬取公司資訊 |
| PM | 解析需求、回答問題 | 撰寫 spec、拆解任務 |
| Engineer | 回答技術問題 | 寫程式碼、執行測試 |
| QA | 分析測試報告 | 執行測試腳本 |
| Finance | 回答成本問題 | 計算 ROI、產生報表 |

---

## 參考文件

- [ADR-003-claude-code-execution.md](./ADR-003-claude-code-execution.md)
- [002-llm-abstraction.md](../architecture/002-llm-abstraction.md)
