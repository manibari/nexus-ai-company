"""
Anthropic Claude LLM Provider
"""

import time
from typing import List, Optional

import anthropic

from app.llm.base import LLMProvider, LLMResponse, Message


class ClaudeProvider(LLMProvider):
    """Anthropic Claude API Provider"""

    provider_name = "claude"

    # Claude Sonnet 4.5 pricing (as of 2026)
    # https://www.anthropic.com/pricing
    cost_per_1k_input = 0.003
    cost_per_1k_output = 0.015

    def __init__(self, api_key: str, model_name: str = "claude-sonnet-4-5-20250929"):
        super().__init__(api_key, model_name)
        self.client = anthropic.AsyncAnthropic(api_key=api_key)

    async def chat(
        self,
        messages: List[Message],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        """發送對話請求到 Claude"""
        start = time.time()

        # 分離 system message 和對話訊息
        system_prompt, formatted_messages = self._format_messages(messages)

        # 呼叫 API
        response = await self.client.messages.create(
            model=self.model_name,
            max_tokens=max_tokens or 4096,
            system=system_prompt,
            messages=formatted_messages,
            temperature=temperature,
        )

        latency = (time.time() - start) * 1000

        # 取得 token 用量
        input_tokens = response.usage.input_tokens
        output_tokens = response.usage.output_tokens

        # 取得回應內容
        content = response.content[0].text if response.content else ""

        return LLMResponse(
            content=content,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=self.calculate_cost(input_tokens, output_tokens),
            model=self.model_name,
            provider=self.provider_name,
            latency_ms=latency,
        )

    def _format_messages(self, messages: List[Message]) -> tuple[str, List[dict]]:
        """
        轉換訊息格式為 Claude 格式

        Claude 的 system message 需要獨立傳遞
        """
        system_prompt = ""
        formatted = []

        for msg in messages:
            if msg.role == "system":
                system_prompt = msg.content
            else:
                formatted.append({"role": msg.role, "content": msg.content})

        return system_prompt, formatted
