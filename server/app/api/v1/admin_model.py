"""Model configuration API — full CRUD for endpoints, groups, instances."""

import uuid

import httpx
from fastapi import APIRouter, Depends
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import BizError
from app.core.permissions import require_permission
from app.dependencies import get_current_admin
from app.models.admin import AdminUser
from app.models.model_config import ModelEndpoint, ModelGroup, ModelInstance
from app.schemas.model_config import (
    EndpointCreate,
    EndpointUpdate,
    GroupCreate,
    GroupUpdate,
    InstanceCreate,
    InstanceUpdate,
    ModelTestRequest,
    EmbeddingTestRequest,
)
from app.services import model_config_service

router = APIRouter()


async def _ensure_single_enabled_group_per_type(
    group_type: str,
    db: AsyncSession,
    exclude_group_id: uuid.UUID | None = None,
) -> None:
    if group_type not in ("llm", "embedding", "review"):
        return
    stmt = select(ModelGroup).where(ModelGroup.type == group_type, ModelGroup.enabled == True)  # noqa: E712
    if exclude_group_id is not None:
        stmt = stmt.where(ModelGroup.id != exclude_group_id)
    existing = (await db.execute(stmt.limit(1))).scalar_one_or_none()
    if existing:
        if group_type == "llm":
            type_label = "LLM 对话"
        elif group_type == "embedding":
            type_label = "Embedding"
        else:
            type_label = "决策"
        raise BizError(code=400, message=f"{type_label} 仅允许一个启用组，请先停用「{existing.name}」")


# ── Overview ─────────────────────────────────────────────────────

@router.get("", dependencies=[Depends(require_permission("model:read"))])
async def get_model_config(
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """获取完整模型配置树"""
    overview = await model_config_service.load_config(db)
    return overview.model_dump(by_alias=True)


# ── Endpoints CRUD ───────────────────────────────────────────────

@router.post("/endpoints", dependencies=[Depends(require_permission("model:update"))])
async def create_endpoint(
    body: EndpointCreate,
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    ep = ModelEndpoint(
        name=body.name,
        provider=body.provider,
        base_url=body.baseUrl,
        api_key=body.apiKey,
    )
    db.add(ep)
    await db.commit()
    await db.refresh(ep)
    await model_config_service.reload_router(db)
    return {"success": True, "id": str(ep.id)}


@router.put("/endpoints/{endpoint_id}", dependencies=[Depends(require_permission("model:update"))])
async def update_endpoint(
    endpoint_id: str,
    body: EndpointUpdate,
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(ModelEndpoint).where(ModelEndpoint.id == uuid.UUID(endpoint_id)))
    ep = result.scalar_one_or_none()
    if not ep:
        raise BizError(code=404, message="接入点不存在")

    if body.name is not None:
        ep.name = body.name
    if body.provider is not None:
        ep.provider = body.provider
    if body.baseUrl is not None:
        ep.base_url = body.baseUrl
    if body.apiKey is not None:
        ep.api_key = body.apiKey

    await db.commit()
    await model_config_service.reload_router(db)
    return {"success": True}


@router.delete("/endpoints/{endpoint_id}", dependencies=[Depends(require_permission("model:delete"))])
async def delete_endpoint(
    endpoint_id: str,
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    ref_result = await db.execute(
        select(ModelInstance).where(ModelInstance.endpoint_id == uuid.UUID(endpoint_id)).limit(1)
    )
    if ref_result.scalar_one_or_none():
        raise BizError(code=400, message="该接入点仍被模型实例引用，请先删除相关实例")

    await db.execute(delete(ModelEndpoint).where(ModelEndpoint.id == uuid.UUID(endpoint_id)))
    await db.commit()
    await model_config_service.reload_router(db)
    return {"success": True}


# ── Groups CRUD ──────────────────────────────────────────────────

@router.post("/groups", dependencies=[Depends(require_permission("model:update"))])
async def create_group(
    body: GroupCreate,
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    if body.type not in ("llm", "embedding", "review"):
        raise BizError(code=400, message="模型组类型必须为 llm / embedding / review（review 即决策模型）")
    if body.enabled:
        await _ensure_single_enabled_group_per_type(body.type, db)

    grp = ModelGroup(
        name=body.name,
        type=body.type,
        strategy=body.strategy,
        enabled=body.enabled,
        priority=body.priority,
    )
    db.add(grp)
    await db.commit()
    await db.refresh(grp)
    await model_config_service.reload_router(db)
    return {"success": True, "id": str(grp.id)}


@router.put("/groups/{group_id}", dependencies=[Depends(require_permission("model:update"))])
async def update_group(
    group_id: str,
    body: GroupUpdate,
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(ModelGroup).where(ModelGroup.id == uuid.UUID(group_id)))
    grp = result.scalar_one_or_none()
    if not grp:
        raise BizError(code=404, message="模型组不存在")

    if body.name is not None:
        grp.name = body.name
    if body.strategy is not None:
        if body.strategy not in ("failover", "round_robin", "weighted"):
            raise BizError(code=400, message="策略必须为 failover / round_robin / weighted")
        grp.strategy = body.strategy
    if body.enabled is not None:
        if body.enabled:
            await _ensure_single_enabled_group_per_type(grp.type, db, exclude_group_id=grp.id)
        grp.enabled = body.enabled
    if body.priority is not None:
        grp.priority = body.priority

    await db.commit()
    await model_config_service.reload_router(db)
    return {"success": True}


@router.delete("/groups/{group_id}", dependencies=[Depends(require_permission("model:delete"))])
async def delete_group(
    group_id: str,
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(ModelGroup).where(ModelGroup.id == uuid.UUID(group_id)))
    grp = result.scalar_one_or_none()
    if not grp:
        raise BizError(code=404, message="模型组不存在")

    await db.execute(delete(ModelInstance).where(ModelInstance.group_id == uuid.UUID(group_id)))
    await db.execute(delete(ModelGroup).where(ModelGroup.id == uuid.UUID(group_id)))
    await db.commit()
    await model_config_service.reload_router(db)
    return {"success": True}


# ── Instances CRUD ───────────────────────────────────────────────

@router.post("/groups/{group_id}/instances", dependencies=[Depends(require_permission("model:update"))])
async def create_instance(
    group_id: str,
    body: InstanceCreate,
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    grp_result = await db.execute(select(ModelGroup).where(ModelGroup.id == uuid.UUID(group_id)))
    if not grp_result.scalar_one_or_none():
        raise BizError(code=404, message="模型组不存在")

    ep_result = await db.execute(select(ModelEndpoint).where(ModelEndpoint.id == uuid.UUID(body.endpointId)))
    if not ep_result.scalar_one_or_none():
        raise BizError(code=404, message="接入点不存在")

    inst = ModelInstance(
        group_id=uuid.UUID(group_id),
        endpoint_id=uuid.UUID(body.endpointId),
        model_name=body.modelName,
        enabled=body.enabled,
        weight=body.weight,
        max_tokens=body.maxTokens,
        temperature=body.temperature,
        priority=body.priority,
    )
    db.add(inst)
    await db.commit()
    await db.refresh(inst)
    await model_config_service.reload_router(db)
    return {"success": True, "id": str(inst.id)}


@router.put("/instances/{instance_id}", dependencies=[Depends(require_permission("model:update"))])
async def update_instance(
    instance_id: str,
    body: InstanceUpdate,
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(ModelInstance).where(ModelInstance.id == uuid.UUID(instance_id)))
    inst = result.scalar_one_or_none()
    if not inst:
        raise BizError(code=404, message="模型实例不存在")

    if body.endpointId is not None:
        ep_result = await db.execute(select(ModelEndpoint).where(ModelEndpoint.id == uuid.UUID(body.endpointId)))
        if not ep_result.scalar_one_or_none():
            raise BizError(code=404, message="接入点不存在")
        inst.endpoint_id = uuid.UUID(body.endpointId)
    if body.modelName is not None:
        inst.model_name = body.modelName
    if body.enabled is not None:
        inst.enabled = body.enabled
    if body.weight is not None:
        inst.weight = body.weight
    if body.maxTokens is not None:
        inst.max_tokens = body.maxTokens
    if body.temperature is not None:
        inst.temperature = body.temperature
    if body.priority is not None:
        inst.priority = body.priority

    await db.commit()
    await model_config_service.reload_router(db)
    return {"success": True}


@router.delete("/instances/{instance_id}", dependencies=[Depends(require_permission("model:delete"))])
async def delete_instance(
    instance_id: str,
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    await db.execute(delete(ModelInstance).where(ModelInstance.id == uuid.UUID(instance_id)))
    await db.commit()
    await model_config_service.reload_router(db)
    return {"success": True}


# ── Test Connectivity ────────────────────────────────────────────

@router.post("/test", dependencies=[Depends(require_permission("model:update"))])
async def test_model_connectivity(
    body: ModelTestRequest,
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """测试模型连通性"""
    base_url = body.base_url.rstrip("/")
    headers = {
        "Authorization": f"Bearer {body.api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": body.model,
        "messages": [{"role": "user", "content": "你好"}],
        "max_tokens": 16,
    }

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(f"{base_url}/chat/completions", headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            reply = data["choices"][0]["message"]["content"]
    except httpx.TimeoutException:
        raise BizError(code=400, message="连接超时，请检查 Base URL 和网络")
    except httpx.HTTPStatusError as e:
        raise BizError(code=400, message=f"API 返回错误: {e.response.status_code}")
    except Exception as e:
        raise BizError(code=400, message=f"连接失败: {str(e)}")

    return {"success": True, "message": "连接成功", "reply": reply}


@router.post("/test-embedding", dependencies=[Depends(require_permission("model:update"))])
async def test_embedding_connectivity(
    body: EmbeddingTestRequest,
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """测试 Embedding 模型连通性"""
    base_url = body.base_url.rstrip("/")
    headers = {
        "Authorization": f"Bearer {body.api_key}",
        "Content-Type": "application/json",
    }
    payload = {"model": body.model, "input": ["测试文本"]}

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(f"{base_url}/embeddings", headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            dim = len(data["data"][0]["embedding"])
    except httpx.TimeoutException:
        raise BizError(code=400, message="连接超时，请检查 Base URL 和网络")
    except httpx.HTTPStatusError as e:
        raise BizError(code=400, message=f"API 返回错误: {e.response.status_code}")
    except Exception as e:
        raise BizError(code=400, message=f"连接失败: {str(e)}")

    return {"success": True, "message": f"连接成功，向量维度: {dim}", "dimension": dim}
