"""LLM service with strategy pattern and router for multi-model support."""

import logging
import random
from abc import ABC, abstractmethod
from typing import AsyncGenerator

import httpx

logger = logging.getLogger(__name__)


class LLMProvider(ABC):
    """Abstract LLM provider interface."""

    @abstractmethod
    async def chat(self, messages: list[dict], stream: bool = False) -> AsyncGenerator[str, None] | str:
        """Send chat completion request."""
        ...

    @abstractmethod
    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for texts."""
        ...


class OpenAICompatibleProvider(LLMProvider):
    """Base provider for OpenAI-compatible APIs (Qwen, GLM, local)."""

    def __init__(self, api_key: str, base_url: str, model: str, name: str = "openai_compatible"):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.name = name
        self.weight: int = 1
        self.client = httpx.AsyncClient(timeout=60.0)

    async def chat(self, messages: list[dict], stream: bool = False) -> AsyncGenerator[str, None] | str:
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        payload = {"model": self.model, "messages": messages, "stream": stream}

        if stream:
            return self._stream_chat(headers, payload)
        else:
            resp = await self.client.post(f"{self.base_url}/chat/completions", headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]

    async def _stream_chat(self, headers: dict, payload: dict) -> AsyncGenerator[str, None]:
        async with self.client.stream(
            "POST", f"{self.base_url}/chat/completions", headers=headers, json=payload
        ) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                if line.startswith("data: "):
                    data = line[6:]
                    if data == "[DONE]":
                        break
                    import json
                    try:
                        chunk = json.loads(data)
                        delta = chunk["choices"][0].get("delta", {})
                        content = delta.get("content", "")
                        if content:
                            yield content
                    except (json.JSONDecodeError, KeyError, IndexError):
                        continue

    async def embed(self, texts: list[str]) -> list[list[float]]:
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        payload = {"model": self.model, "input": texts}
        resp = await self.client.post(f"{self.base_url}/embeddings", headers=headers, json=payload)
        resp.raise_for_status()
        data = resp.json()
        return [item["embedding"] for item in data["data"]]


class QwenProvider(OpenAICompatibleProvider):
    """通义千问 provider."""
    def __init__(self, api_key: str, base_url: str, model: str):
        super().__init__(api_key, base_url, model, name="qwen")


class GLMProvider(OpenAICompatibleProvider):
    """智谱 GLM provider."""
    def __init__(self, api_key: str, base_url: str, model: str):
        super().__init__(api_key, base_url, model, name="glm")


class LocalProvider(OpenAICompatibleProvider):
    """本地模型 provider (Ollama/vLLM)."""
    def __init__(self, api_key: str, base_url: str, model: str):
        super().__init__(api_key, base_url, model, name="local")


class LLMRouter:
    """Model router with failover, round-robin, and weighted load balancing."""

    def __init__(self):
        self.providers: list[LLMProvider] = []
        self.review_provider: LLMProvider | None = None
        self.strategy: str = "failover"  # failover / round_robin / weighted
        self._current_index: int = 0

    def add_provider(self, provider: LLMProvider):
        self.providers.append(provider)

    def set_review_provider(self, provider: LLMProvider):
        self.review_provider = provider

    def _get_provider(self) -> LLMProvider:
        if not self.providers:
            raise RuntimeError("No LLM providers configured")
        if self.strategy == "round_robin":
            provider = self.providers[self._current_index % len(self.providers)]
            self._current_index += 1
            return provider
        if self.strategy == "weighted":
            weights = [getattr(p, "weight", 1) for p in self.providers]
            return random.choices(self.providers, weights=weights, k=1)[0]
        # Default: failover — return first provider
        return self.providers[0]

    async def chat(self, messages: list[dict], stream: bool = False) -> AsyncGenerator[str, None] | str:
        last_error = None
        for i, provider in enumerate(self.providers):
            try:
                result = await provider.chat(messages, stream=stream)
                return result
            except Exception as e:
                logger.warning("LLM provider %s failed: %s", getattr(provider, 'name', i), e)
                last_error = e
                continue
        raise RuntimeError(f"All LLM providers failed. Last error: {last_error}")

    async def review_chat(self, messages: list[dict]) -> str:
        """Use review model for hallucination checking."""
        provider = self.review_provider or self._get_provider()
        return await provider.chat(messages, stream=False)

    async def embed(self, texts: list[str]) -> list[list[float]]:
        provider = self._get_provider()
        return await provider.embed(texts)


# Singleton instance — initialized empty, populated by model_config_service.reload_router()
llm_router = LLMRouter()
