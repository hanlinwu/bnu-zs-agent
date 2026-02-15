"""Dual-model review service for hallucination prevention."""

import logging

from app.services.llm_service import llm_router

logger = logging.getLogger(__name__)

REVIEW_PROMPT_TEMPLATE = """你是一个事实核查助手。请对比以下"回答"与"知识库来源"的一致性。

用户提问：{question}

AI回答：{answer}

知识库来源：
{sources}

请判断：
1. 回答中的事实性信息是否与知识库来源一致？
2. 回答是否包含知识库中没有提及的断言性内容？

只回答 "PASSED" 或 "FLAGGED"，不要其他内容。
如果回答基本与来源一致且没有明显错误，回答 PASSED。
如果回答包含来源中没有的具体数字、日期、保证性承诺等，回答 FLAGGED。"""


async def verify(question: str, answer: str, sources: str) -> dict:
    """Verify answer against knowledge sources using review model.

    Returns:
        {"passed": True/False, "detail": str}
    """
    if not sources:
        # No sources to check against, pass by default
        return {"passed": True, "detail": "no_sources"}

    prompt = REVIEW_PROMPT_TEMPLATE.format(
        question=question,
        answer=answer,
        sources=sources,
    )

    try:
        result = await llm_router.review_chat([
            {"role": "system", "content": "你是事实核查助手，只回答 PASSED 或 FLAGGED。"},
            {"role": "user", "content": prompt},
        ])
        result_stripped = result.strip().upper()
        passed = "PASSED" in result_stripped
        return {"passed": passed, "detail": result_stripped}
    except Exception as e:
        logger.error("Review service failed: %s", e)
        # Fail open — allow the answer but log the failure
        return {"passed": True, "detail": f"review_error: {e}"}
