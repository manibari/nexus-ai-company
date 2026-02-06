"""
LLM Provider Base Classes and Interfaces
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class Message:
    """對話訊息"""
    role: str  # "system" | "user" | "assistant"
    content: str


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


class LLMProvider(ABC):
    """
    LLM Provider 抽象基底類別

    所有 LLM Provider（Gemini, Claude, OpenAI）都必須實作此介面
    """

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
        max_tokens: Optional[int] = None,
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
