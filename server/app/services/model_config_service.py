"""Model configuration service — loads config from DB and builds LLM router."""

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.model_config import ModelEndpoint, ModelGroup, ModelInstance
from app.schemas.model_config import (
    EndpointResponse,
    GroupResponse,
    InstanceResponse,
    ModelConfigOverview,
)

logger = logging.getLogger(__name__)

# ── Cached embedding config for use by embedding_service ──
_embedding_config: dict | None = None


def _mask_key(key: str) -> str:
    if not key or len(key) <= 8:
        return "****"
    return f"{key[:4]}****{key[-4:]}"


def _endpoint_to_response(ep: ModelEndpoint) -> EndpointResponse:
    return EndpointResponse(
        id=str(ep.id),
        name=ep.name,
        provider=ep.provider,
        baseUrl=ep.base_url,
        apiKey=_mask_key(ep.api_key),
        createdAt=ep.created_at.isoformat() if ep.created_at else "",
    )


def _instance_to_response(inst: ModelInstance, include_endpoint: bool = True) -> InstanceResponse:
    ep_resp = None
    if include_endpoint and inst.endpoint:
        ep_resp = _endpoint_to_response(inst.endpoint)
    return InstanceResponse(
        id=str(inst.id),
        groupId=str(inst.group_id),
        endpointId=str(inst.endpoint_id),
        modelName=inst.model_name,
        enabled=inst.enabled,
        weight=inst.weight,
        maxTokens=inst.max_tokens,
        temperature=inst.temperature,
        priority=inst.priority,
        createdAt=inst.created_at.isoformat() if inst.created_at else "",
        endpoint=ep_resp,
    )


def _group_to_response(grp: ModelGroup) -> GroupResponse:
    return GroupResponse(
        id=str(grp.id),
        name=grp.name,
        type=grp.type,
        strategy=grp.strategy,
        enabled=grp.enabled,
        priority=grp.priority,
        createdAt=grp.created_at.isoformat() if grp.created_at else "",
        instances=[_instance_to_response(i) for i in (grp.instances or [])],
    )


async def load_config(db: AsyncSession) -> ModelConfigOverview:
    """Load full model configuration from DB."""
    ep_result = await db.execute(select(ModelEndpoint).order_by(ModelEndpoint.created_at))
    endpoints = ep_result.scalars().all()

    grp_result = await db.execute(
        select(ModelGroup)
        .options(selectinload(ModelGroup.instances).selectinload(ModelInstance.endpoint))
        .order_by(ModelGroup.priority, ModelGroup.created_at)
    )
    groups = grp_result.scalars().all()

    return ModelConfigOverview(
        endpoints=[_endpoint_to_response(ep) for ep in endpoints],
        groups=[_group_to_response(grp) for grp in groups],
    )


async def reload_router(db: AsyncSession) -> None:
    """Rebuild the LLM router from DB config and update the singleton."""
    global _embedding_config

    grp_result = await db.execute(
        select(ModelGroup)
        .options(selectinload(ModelGroup.instances).selectinload(ModelInstance.endpoint))
        .order_by(ModelGroup.priority)
    )
    groups = grp_result.scalars().all()

    from app.services.llm_service import (
        OpenAICompatibleProvider,
        QwenProvider,
        GLMProvider,
        LocalProvider,
    )
    import app.services.llm_service as llm_mod

    provider_map = {
        "qwen": QwenProvider,
        "glm": GLMProvider,
        "local": LocalProvider,
    }

    # Mutate the existing singleton so all importers see the update
    router = llm_mod.llm_router
    router.providers.clear()
    router.review_provider = None
    router.strategy = "failover"
    router._current_index = 0
    _embedding_config = None

    for grp in groups:
        if not grp.enabled:
            continue

        enabled_instances = [i for i in grp.instances if i.enabled and i.endpoint]
        if not enabled_instances:
            continue

        if grp.type == "embedding":
            # Use the first enabled instance for embedding config
            inst = enabled_instances[0]
            ep = inst.endpoint
            _embedding_config = {
                "base_url": ep.base_url,
                "api_key": ep.api_key,
                "model": inst.model_name,
            }
            continue

        if grp.type in ("llm", "review"):
            # Sort instances by priority
            sorted_instances = sorted(enabled_instances, key=lambda i: i.priority)

            for inst in sorted_instances:
                ep = inst.endpoint
                cls = provider_map.get(ep.provider, OpenAICompatibleProvider)
                provider = cls(
                    api_key=ep.api_key,
                    base_url=ep.base_url,
                    model=inst.model_name,
                )

                if grp.type == "llm":
                    router.add_provider(provider)
                elif grp.type == "review":
                    if router.review_provider is None:
                        router.set_review_provider(provider)

            # Apply group strategy to the router (for LLM groups)
            if grp.type == "llm":
                router.strategy = grp.strategy

    logger.info(
        "LLM router reloaded: %d providers, review=%s, strategy=%s",
        len(router.providers),
        "yes" if router.review_provider else "no",
        router.strategy,
    )


def get_embedding_config() -> dict | None:
    """Return the cached embedding config (set by reload_router)."""
    return _embedding_config
