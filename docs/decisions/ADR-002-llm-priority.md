# ADR-002: LLM Provider 優先順序

> **狀態**: 已採納
> **日期**: 2026-02-06
> **決策者**: CEO

---

## 背景

在 ADR-001 中，我們選擇 Gemini 作為初始 LLM Provider。經過進一步考量，決定調整優先順序。

## 決策

**Claude Code 作為 AI Agent 的首選 LLM Provider**

優先順序：
1. **Claude** (Primary) - Agent 執行任務時的預設選擇
2. **Gemini** (Secondary) - 備用或特定任務使用
3. **OpenAI** (Tertiary) - 備用

## 理由

1. **Claude Code 整合**：系統本身使用 Claude Code 開發，保持一致性
2. **工具使用能力**：Claude 在 function calling 和 tool use 方面表現優異
3. **長上下文**：Claude 支援較長的上下文窗口，適合複雜任務
4. **一致的輸出格式**：減少解析錯誤

## 實作變更

```python
# .env 預設值
LLM_PROVIDER=claude

# LLMProviderFactory 優先順序
_priority = ["claude", "gemini", "openai"]
```

## 成本考量

| Provider | Input ($/1M tokens) | Output ($/1M tokens) |
|----------|---------------------|----------------------|
| Claude Sonnet 4.5 | $3.00 | $15.00 |
| Gemini 1.5 Pro | $1.25 | $3.75 |
| GPT-4o | $5.00 | $15.00 |

Claude 成本較 Gemini 高，但品質與穩定性的提升值得這個投資。

## Fallback 機制

```
Claude API 失敗
    ↓ (retry 3 次)
Gemini (fallback)
    ↓ (retry 3 次)
OpenAI (last resort)
    ↓ (失敗)
錯誤通知 CEO
```

---

## 參考文件

- [ADR-001-tech-stack.md](./ADR-001-tech-stack.md)
- [002-llm-abstraction.md](../architecture/002-llm-abstraction.md)
