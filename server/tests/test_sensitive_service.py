"""Tests for sensitive word filtering service."""

import pytest
from unittest.mock import AsyncMock, patch
from app.services.sensitive_service import check_sensitive, FilterResult


@pytest.mark.asyncio
async def test_block_level_word():
    mock_words = {"违规内容": "block", "正常词": "warn"}
    with patch("app.services.sensitive_service.load_sensitive_words", new_callable=AsyncMock, return_value=mock_words):
        result = await check_sensitive("这里有违规内容")
        assert result.action == "block"
        assert "违规内容" in result.matched_words


@pytest.mark.asyncio
async def test_warn_level_word():
    mock_words = {"敏感话题": "warn"}
    with patch("app.services.sensitive_service.load_sensitive_words", new_callable=AsyncMock, return_value=mock_words):
        result = await check_sensitive("讨论敏感话题")
        assert result.action == "warn"
        assert "敏感话题" in result.matched_words


@pytest.mark.asyncio
async def test_clean_text_passes():
    mock_words = {"违规": "block"}
    with patch("app.services.sensitive_service.load_sensitive_words", new_callable=AsyncMock, return_value=mock_words):
        result = await check_sensitive("北师大心理学怎么样")
        assert result.action == "pass"
        assert result.matched_words == []


@pytest.mark.asyncio
async def test_empty_word_list_passes():
    with patch("app.services.sensitive_service.load_sensitive_words", new_callable=AsyncMock, return_value={}):
        result = await check_sensitive("任何内容")
        assert result.action == "pass"
