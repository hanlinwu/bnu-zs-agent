"""Tests for LLM service."""

import random

import pytest

from app.services.llm_service import LLMRouter, LLMProvider, OpenAICompatibleProvider


def test_llm_router_failover():
    """Test that router is created and strategy defaults to failover."""
    router = LLMRouter()
    assert router.strategy == "failover"
    assert len(router.providers) == 0


def test_llm_router_add_provider():
    router = LLMRouter()
    provider = OpenAICompatibleProvider(
        api_key="test", base_url="http://localhost:8080", model="test-model"
    )
    router.add_provider(provider)
    assert len(router.providers) == 1


def test_llm_router_round_robin():
    router = LLMRouter()
    router.strategy = "round_robin"
    p1 = OpenAICompatibleProvider(api_key="k1", base_url="http://a", model="m1", name="p1")
    p2 = OpenAICompatibleProvider(api_key="k2", base_url="http://b", model="m2", name="p2")
    router.add_provider(p1)
    router.add_provider(p2)

    assert router._get_provider().name == "p1"
    assert router._get_provider().name == "p2"
    assert router._get_provider().name == "p1"


def test_llm_router_no_providers_raises():
    import pytest
    router = LLMRouter()
    with pytest.raises(RuntimeError):
        router._get_provider()


def test_review_provider_separate():
    router = LLMRouter()
    main = OpenAICompatibleProvider(api_key="k", base_url="http://a", model="big", name="main")
    review = OpenAICompatibleProvider(api_key="k", base_url="http://b", model="small", name="review")
    router.add_provider(main)
    router.set_review_provider(review)
    assert router.review_provider.name == "review"


class MockProvider(LLMProvider):
    def __init__(self, name: str, should_fail: bool = False):
        self.name = name
        self.model = name
        self.should_fail = should_fail
        self.calls = 0
        self.weight = 1

    async def chat(self, messages: list[dict], stream: bool = False):
        self.calls += 1
        if self.should_fail:
            raise RuntimeError(f"{self.name} failed")
        return self.name

    async def embed(self, texts: list[str]) -> list[list[float]]:
        return [[0.0] for _ in texts]


@pytest.mark.asyncio
async def test_chat_round_robin_sequence_uses_strategy():
    router = LLMRouter()
    router.strategy = "round_robin"
    p1 = MockProvider("p1")
    p2 = MockProvider("p2")
    router.add_provider(p1)
    router.add_provider(p2)

    assert await router.chat([{"role": "user", "content": "hi"}]) == "p1"
    assert await router.chat([{"role": "user", "content": "hi"}]) == "p2"


@pytest.mark.asyncio
async def test_chat_weighted_first_then_fallback(monkeypatch):
    router = LLMRouter()
    router.strategy = "weighted"
    first = MockProvider("weighted_fail", should_fail=True)
    second = MockProvider("fallback_ok")
    first.weight = 100
    second.weight = 1
    router.add_provider(first)
    router.add_provider(second)

    monkeypatch.setattr(random, "choices", lambda providers, weights, k: [providers[0]])
    result = await router.chat([{"role": "user", "content": "hi"}])

    assert result == "fallback_ok"
    assert first.calls == 1
    assert second.calls == 1
