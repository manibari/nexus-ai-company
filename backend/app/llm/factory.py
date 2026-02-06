"""
LLM Provider Factory
"""

import os
from typing import Optional

from app.llm.base import LLMProvider
from app.llm.claude import ClaudeProvider
from app.llm.gemini import GeminiProvider
from app.llm.openai_provider import OpenAIProvider


class LLMProviderFactory:
    """
    工廠模式建立 LLM Provider

    使用方式：
        provider = LLMProviderFactory.create("gemini")
        response = await provider.chat([...])
    """

    _providers = {
        "gemini": GeminiProvider,
        "claude": ClaudeProvider,
        "openai": OpenAIProvider,
    }

    _default_models = {
        "gemini": "gemini-1.5-pro",
        "claude": "claude-sonnet-4-5-20250929",
        "openai": "gpt-4o",
    }

    _env_keys = {
        "gemini": "GEMINI_API_KEY",
        "claude": "ANTHROPIC_API_KEY",
        "openai": "OPENAI_API_KEY",
    }

    @classmethod
    def create(
        cls,
        provider: str,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None,
    ) -> LLMProvider:
        """
        建立 LLM Provider 實例

        Args:
            provider: Provider 名稱 ("gemini", "claude", "openai")
            api_key: API Key（如果沒提供，會從環境變數讀取）
            model_name: 模型名稱（如果沒提供，使用預設值）

        Returns:
            LLMProvider 實例

        Raises:
            ValueError: 未知的 provider 名稱
            ValueError: 找不到 API Key
        """
        if provider not in cls._providers:
            raise ValueError(
                f"Unknown provider: {provider}. "
                f"Available: {list(cls._providers.keys())}"
            )

        # 取得 API Key
        if api_key is None:
            env_key = cls._env_keys[provider]
            api_key = os.getenv(env_key)
            if not api_key:
                raise ValueError(
                    f"API key not found. Please set {env_key} environment variable."
                )

        # 取得模型名稱
        if model_name is None:
            model_name = cls._get_model_from_env(provider)

        provider_class = cls._providers[provider]
        return provider_class(api_key, model_name)

    @classmethod
    def _get_model_from_env(cls, provider: str) -> str:
        """從環境變數取得模型名稱，若無則使用預設值"""
        env_model_keys = {
            "gemini": "GEMINI_MODEL",
            "claude": "CLAUDE_MODEL",
            "openai": "OPENAI_MODEL",
        }

        model_from_env = os.getenv(env_model_keys.get(provider, ""))
        return model_from_env or cls._default_models[provider]

    @classmethod
    def get_current_provider(cls) -> LLMProvider:
        """
        取得當前設定的 Provider

        根據 LLM_PROVIDER 環境變數決定
        """
        provider_name = os.getenv("LLM_PROVIDER", "gemini")
        return cls.create(provider_name)

    @classmethod
    def list_providers(cls) -> list[str]:
        """列出所有可用的 Provider"""
        return list(cls._providers.keys())
