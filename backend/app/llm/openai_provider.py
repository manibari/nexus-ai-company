"""
OpenAI GPT LLM Provider
"""

import time
from typing import List, Optional

import openai

from app.llm.base import LLMProvider, LLMResponse, Message


class OpenAIProvider(LLMProvider):
    """OpenAI GPT API Provider"""

    provider_name = "openai"

    # GPT-4o pricing (as of 2026)
    # https://openai.com/pricing
    cost_per_1k_input = 0.005
    cost_per_1k_output = 0.015

    def __init__(self, api_key: str, model_name: str = "gpt-4o"):
        super().__init__(api_key, model_name)
        self.client = openai.AsyncOpenAI(api_key=api_key)

    async def chat(
        self,
        messages: List[Message],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        """發送對話請求到 OpenAI"""
        start = time.time()

        # 轉換訊息格式
        formatted = self._format_messages(messages)

        # 呼叫 API
        response = await self.client.chat.completions.create(
            model=self.model_name,
            messages=formatted,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        latency = (time.time() - start) * 1000

        # 取得 token 用量
        input_tokens = response.usage.prompt_tokens
        output_tokens = response.usage.completion_tokens

        # 取得回應內容
        content = response.choices[0].message.content or ""

        return LLMResponse(
            content=content,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=self.calculate_cost(input_tokens, output_tokens),
            model=self.model_name,
            provider=self.provider_name,
            latency_ms=latency,
        )

    def _format_messages(self, messages: List[Message]) -> List[dict]:
        """
        轉換訊息格式為 OpenAI 格式

        OpenAI 原生支援 system, user, assistant 角色
        """
        return [{"role": msg.role, "content": msg.content} for msg in messages]
