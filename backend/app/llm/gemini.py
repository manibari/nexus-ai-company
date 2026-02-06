"""
Google Gemini LLM Provider
"""

import time
from typing import List, Optional

import google.generativeai as genai

from app.llm.base import LLMProvider, LLMResponse, Message


class GeminiProvider(LLMProvider):
    """Google Gemini API Provider"""

    provider_name = "gemini"

    # Gemini 1.5 Pro pricing (as of 2026)
    # https://ai.google.dev/pricing
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
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        """發送對話請求到 Gemini"""
        start = time.time()

        # 轉換訊息格式
        formatted = self._format_messages(messages)

        # 建立 generation config
        generation_config = {"temperature": temperature}
        if max_tokens:
            generation_config["max_output_tokens"] = max_tokens

        # 呼叫 API（使用 sync 版本，因為 Gemini SDK 的 async 支援有限）
        response = self.client.generate_content(
            formatted,
            generation_config=generation_config,
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
            latency_ms=latency,
        )

    def _format_messages(self, messages: List[Message]) -> List[dict]:
        """
        轉換訊息格式為 Gemini 格式

        Gemini 使用 'user' 和 'model' 角色
        System message 需要特殊處理
        """
        formatted = []
        system_prompt = None

        for msg in messages:
            if msg.role == "system":
                system_prompt = msg.content
            elif msg.role == "user":
                content = msg.content
                # 如果有 system prompt，附加到第一個 user message
                if system_prompt and not formatted:
                    content = f"[System Instruction]\n{system_prompt}\n\n[User Message]\n{content}"
                    system_prompt = None
                formatted.append({"role": "user", "parts": [content]})
            elif msg.role == "assistant":
                formatted.append({"role": "model", "parts": [msg.content]})

        return formatted
