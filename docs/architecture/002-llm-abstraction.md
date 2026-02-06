# 002: LLM 抽象層設計

> **版本**: 1.0.0
> **日期**: 2026-02-06

---

## 設計目標

1. **Provider 可切換**：前端可動態選擇 Gemini / Claude / OpenAI
2. **統一介面**：所有 Agent 使用相同的呼叫方式
3. **成本追蹤**：每次呼叫記錄 Token 用量與費用
4. **錯誤處理**：統一的 retry 與 fallback 機制

---

## 類別圖

```
                    ┌─────────────────────────┐
                    │   <<abstract>>          │
                    │   LLMProvider           │
                    ├─────────────────────────┤
                    │ + model_name: str       │
                    │ + cost_per_1k_input: f  │
                    │ + cost_per_1k_output: f │
                    ├─────────────────────────┤
                    │ + chat(messages) -> str │
                    │ + count_tokens() -> int │
                    │ + get_cost() -> float   │
                    └───────────┬─────────────┘
                                │
          ┌─────────────────────┼─────────────────────┐
          │                     │                     │
          ▼                     ▼                     ▼
┌─────────────────┐   ┌─────────────────┐   ┌─────────────────┐
│  GeminiProvider │   │  ClaudeProvider │   │  OpenAIProvider │
├─────────────────┤   ├─────────────────┤   ├─────────────────┤
│ - api_key       │   │ - api_key       │   │ - api_key       │
│ - client        │   │ - client        │   │ - client        │
├─────────────────┤   ├─────────────────┤   ├─────────────────┤
│ + chat()        │   │ + chat()        │   │ + chat()        │
│ + count_tokens()│   │ + count_tokens()│   │ + count_tokens()│
└─────────────────┘   └─────────────────┘   └─────────────────┘
```

---

## 介面定義

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Dict, Any, Optional


@dataclass
class LLMResponse:
    """LLM 回應的標準格式"""
    content: str
    input_tokens: int
    output_tokens: int
    cost_usd: float
    model: str
    provider: str
    latency_ms: float


@dataclass
class Message:
    """對話訊息"""
    role: str  # "system" | "user" | "assistant"
    content: str


class LLMProvider(ABC):
    """LLM Provider 抽象基底類別"""

    def __init__(self, api_key: str, model_name: str):
        self.api_key = api_key
        self.model_name = model_name

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Provider 名稱 (gemini, claude, openai)"""
        pass

    @property
    @abstractmethod
    def cost_per_1k_input(self) -> float:
        """每 1000 input tokens 的成本 (USD)"""
        pass

    @property
    @abstractmethod
    def cost_per_1k_output(self) -> float:
        """每 1000 output tokens 的成本 (USD)"""
        pass

    @abstractmethod
    async def chat(
        self,
        messages: List[Message],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None
    ) -> LLMResponse:
        """
        發送對話請求

        Args:
            messages: 對話歷史
            temperature: 創意度 (0-1)
            max_tokens: 最大回應長度

        Returns:
            LLMResponse: 標準化的回應物件
        """
        pass

    def calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """計算本次呼叫成本"""
        input_cost = (input_tokens / 1000) * self.cost_per_1k_input
        output_cost = (output_tokens / 1000) * self.cost_per_1k_output
        return round(input_cost + output_cost, 6)
```

---

## Provider 實作範例

### Gemini Provider

```python
import google.generativeai as genai
import time

class GeminiProvider(LLMProvider):

    provider_name = "gemini"

    # Gemini 1.5 Pro pricing (as of 2026)
    cost_per_1k_input = 0.00125
    cost_per_1k_output = 0.00375

    def __init__(self, api_key: str, model_name: str = "gemini-1.5-pro"):
        super().__init__(api_key, model_name)
        genai.configure(api_key=api_key)
        self.client = genai.GenerativeModel(model_name)

    async def chat(
        self,
        messages: List[Message],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None
    ) -> LLMResponse:
        start = time.time()

        # 轉換訊息格式
        formatted = self._format_messages(messages)

        # 呼叫 API
        response = await self.client.generate_content_async(
            formatted,
            generation_config={
                "temperature": temperature,
                "max_output_tokens": max_tokens
            }
        )

        latency = (time.time() - start) * 1000

        # 取得 token 用量
        input_tokens = response.usage_metadata.prompt_token_count
        output_tokens = response.usage_metadata.candidates_token_count

        return LLMResponse(
            content=response.text,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=self.calculate_cost(input_tokens, output_tokens),
            model=self.model_name,
            provider=self.provider_name,
            latency_ms=latency
        )
```

---

## Provider Factory

```python
class LLMProviderFactory:
    """工廠模式建立 Provider"""

    _providers = {
        "gemini": GeminiProvider,
        "claude": ClaudeProvider,
        "openai": OpenAIProvider,
    }

    @classmethod
    def create(
        cls,
        provider: str,
        api_key: str,
        model_name: Optional[str] = None
    ) -> LLMProvider:
        if provider not in cls._providers:
            raise ValueError(f"Unknown provider: {provider}")

        provider_class = cls._providers[provider]

        # 使用預設模型如果沒有指定
        if model_name is None:
            model_name = cls._get_default_model(provider)

        return provider_class(api_key, model_name)

    @staticmethod
    def _get_default_model(provider: str) -> str:
        defaults = {
            "gemini": "gemini-1.5-pro",
            "claude": "claude-sonnet-4-5-20250929",
            "openai": "gpt-4o",
        }
        return defaults[provider]
```

---

## 錯誤處理與 Retry

```python
from tenacity import retry, stop_after_attempt, wait_exponential

class RobustLLMProvider:
    """包裝 Provider 加入 retry 邏輯"""

    def __init__(self, provider: LLMProvider, fallback: Optional[LLMProvider] = None):
        self.provider = provider
        self.fallback = fallback

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    async def chat(self, messages: List[Message], **kwargs) -> LLMResponse:
        try:
            return await self.provider.chat(messages, **kwargs)
        except Exception as e:
            if self.fallback:
                logger.warning(f"Primary failed, using fallback: {e}")
                return await self.fallback.chat(messages, **kwargs)
            raise
```

---

## 使用範例

```python
# 建立 Provider
provider = LLMProviderFactory.create(
    provider="gemini",
    api_key=os.getenv("GEMINI_API_KEY")
)

# 發送請求
response = await provider.chat([
    Message(role="system", content="You are a sales agent."),
    Message(role="user", content="Draft an outreach email.")
])

print(f"Response: {response.content}")
print(f"Cost: ${response.cost_usd}")
print(f"Latency: {response.latency_ms}ms")
```

---

## Token 審計整合

每次 LLM 呼叫後，自動記錄到 `ledger` 表：

```python
async def audit_llm_call(response: LLMResponse, agent_id: str, task_id: str):
    """記錄 LLM 呼叫到財務帳本"""
    await db.execute(
        ledger.insert().values(
            agent_id=agent_id,
            task_id=task_id,
            provider=response.provider,
            model=response.model,
            input_tokens=response.input_tokens,
            output_tokens=response.output_tokens,
            cost_usd=response.cost_usd,
            timestamp=datetime.utcnow()
        )
    )
```

---

## 參考文件

- [ADR-001-tech-stack.md](../decisions/ADR-001-tech-stack.md)
- [003-agent-communication.md](./003-agent-communication.md)
