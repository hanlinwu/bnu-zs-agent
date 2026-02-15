"""Tests for LLM service."""

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
