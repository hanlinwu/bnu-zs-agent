"""Seed data for RBAC roles, permissions, and default super admin.

The seeding is idempotent:
- Missing roles/permissions are added on every startup.
- Missing role-permission bindings are补齐 without deleting existing custom bindings.
- Default admin and super admin assignment are ensured.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session_factory
from app.models.role import Role, Permission, RolePermission, AdminRole
from app.models.admin import AdminUser
from app.models.calendar import AdmissionCalendar
from app.models.review_workflow import ReviewWorkflow, ResourceWorkflowBinding
from app.models.system_config import SystemConfig

# 8 preset roles
ROLES = [
    {"code": "super_admin", "name": "超级管理员", "role_type": "admin", "is_system": True, "description": "系统最高权限，可管理所有功能"},
    {"code": "reviewer", "name": "内容审核员", "role_type": "admin", "is_system": True, "description": "负责知识库和多媒体内容审核"},
    {"code": "admin", "name": "普通管理员", "role_type": "admin", "is_system": True, "description": "日常管理操作"},
    {"code": "teacher", "name": "招生老师", "role_type": "admin", "is_system": True, "description": "查看招生相关信息"},
    {"code": "gaokao", "name": "高考生", "role_type": "user", "is_system": True, "description": "参加高考的考生"},
    {"code": "kaoyan", "name": "考研生", "role_type": "user", "is_system": True, "description": "考研学生"},
    {"code": "international", "name": "国际学生", "role_type": "user", "is_system": True, "description": "国际留学生"},
    {"code": "parent", "name": "家长", "role_type": "user", "is_system": True, "description": "考生家长"},
]

# Resource namespace used by route-level permission checks.
# Keep both `sensitive` and `sensitive_word` for backward compatibility.
RESOURCES = [
    "knowledge",
    "user",
    "admin",
    "model",
    "log",
    "media",
    "sensitive",
    "sensitive_word",
    "calendar",
    "role",
    "dashboard",
    "conversation",
    "system_config",
]
ACTIONS = ["create", "read", "update", "delete", "approve", "export", "ban"]

# Permission matrix per admin role
ROLE_PERMISSIONS = {
    "super_admin": {r: ACTIONS for r in RESOURCES},  # all permissions
    "reviewer": {
        "knowledge": ["read", "approve"],
        "user": ["read"],
        "media": ["read", "approve"],
        "sensitive": ["read"],
        "log": ["read"],
        "conversation": ["read"],
    },
    "admin": {
        "knowledge": ["read", "create"],
        "user": ["read"],
        "model": ["read"],
        "system_config": ["read", "update"],
        "log": ["read"],
        "media": ["read", "create"],
        "sensitive": ["read"],
        "calendar": ["read"],
        "dashboard": ["read"],
        "conversation": ["read"],
    },
    "teacher": {
        "knowledge": ["read"],
        "user": ["read"],
        "media": ["read"],
        "calendar": ["read"],
        "conversation": ["read"],
    },
}


async def seed_roles_and_permissions() -> None:
    """Upsert preset roles, permissions, and default admin."""
    session_factory = get_session_factory()
    async with session_factory() as session:
        # Roles: fetch existing and create missing
        role_result = await session.execute(select(Role))
        role_map: dict[str, Role] = {r.code: r for r in role_result.scalars().all()}
        for role_data in ROLES:
            if role_data["code"] in role_map:
                continue
            role = Role(**role_data)
            session.add(role)
            role_map[role_data["code"]] = role

        # Permissions: fetch existing and create missing
        perm_result = await session.execute(select(Permission))
        perm_map: dict[str, Permission] = {p.code: p for p in perm_result.scalars().all()}
        for resource in RESOURCES:
            for action in ACTIONS:
                code = f"{resource}:{action}"
                if code in perm_map:
                    continue
                perm = Permission(
                    code=code,
                    name=f"{resource} {action}",
                    resource=resource,
                    action=action,
                )
                session.add(perm)
                perm_map[code] = perm

        await session.flush()

        # Existing bindings for idempotent insertion
        rp_result = await session.execute(select(RolePermission.role_id, RolePermission.permission_id))
        existing_bindings = {(row[0], row[1]) for row in rp_result.all()}

        # Ensure role-permission associations
        for role_code, resource_actions in ROLE_PERMISSIONS.items():
            role = role_map.get(role_code)
            if not role:
                continue
            for resource, actions in resource_actions.items():
                for action in actions:
                    perm_code = f"{resource}:{action}"
                    perm = perm_map.get(perm_code)
                    if not perm:
                        continue
                    key = (role.id, perm.id)
                    if key in existing_bindings:
                        continue
                    session.add(RolePermission(role_id=role.id, permission_id=perm.id))
                    existing_bindings.add(key)

        # Create default super admin if missing (password: admin123)
        from app.core.security import hash_password
        admin_result = await session.execute(select(AdminUser).where(AdminUser.username == "admin"))
        default_admin = admin_result.scalar_one_or_none()
        if not default_admin:
            default_admin = AdminUser(
                username="admin",
                password_hash=hash_password("admin123"),
                real_name="系统管理员",
                status="active",
            )
            session.add(default_admin)
            await session.flush()

        # Ensure super_admin role assignment for default admin
        super_admin_role = role_map.get("super_admin")
        if super_admin_role:
            ar_result = await session.execute(
                select(AdminRole).where(
                    AdminRole.admin_id == default_admin.id,
                    AdminRole.role_id == super_admin_role.id,
                )
            )
            if ar_result.scalar_one_or_none() is None:
                session.add(AdminRole(admin_id=default_admin.id, role_id=super_admin_role.id))

        await session.commit()


# Default calendar periods (day-precise)
from datetime import date as _date

CALENDAR_PERIODS = [
    {"period_name": "备考期", "year": 2026, "start_date": _date(2026, 1, 1), "end_date": _date(2026, 5, 31), "tone_config": {"style": "motivational", "description": "激励、备考建议、专业前景", "keywords": ["高考加油", "备考建议", "专业介绍"]}, "is_active": True},
    {"period_name": "高考后/报名期", "year": 2026, "start_date": _date(2026, 6, 1), "end_date": _date(2026, 7, 31), "tone_config": {"style": "guidance", "description": "志愿填报、分数线预测、报名指南", "keywords": ["志愿填报", "分数线", "报名指南"]}, "is_active": True},
    {"period_name": "录取查询期", "year": 2026, "start_date": _date(2026, 8, 1), "end_date": _date(2026, 9, 30), "tone_config": {"style": "enrollment", "description": "录取结果查询、入学准备清单", "keywords": ["录取查询", "入学准备", "报到须知"]}, "is_active": True},
    {"period_name": "常态期", "year": 2026, "start_date": _date(2026, 10, 1), "end_date": _date(2026, 12, 31), "tone_config": {"style": "general", "description": "校园文化、师资力量、国际交流", "keywords": ["校园文化", "师资力量", "国际交流"]}, "is_active": True},
]


async def _migrate_calendar_columns() -> None:
    """Ensure admission_calendar has year + start_date/end_date columns."""
    from sqlalchemy import text as sa_text

    session_factory = get_session_factory()
    async with session_factory() as session:
        # Check which columns exist
        result = await session.execute(sa_text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name = 'admission_calendar'"
        ))
        columns = {row[0] for row in result.all()}
        if not columns:
            return  # table doesn't exist yet

        changed = False

        # --- Phase 1: old month-based → date-based ---
        if "start_month" in columns:
            if "start_date" not in columns:
                await session.execute(sa_text(
                    "ALTER TABLE admission_calendar ADD COLUMN start_date DATE"
                ))
                await session.execute(sa_text(
                    "ALTER TABLE admission_calendar ADD COLUMN end_date DATE"
                ))
            # Migrate data from month columns
            await session.execute(sa_text(
                "UPDATE admission_calendar "
                "SET start_date = make_date(year, start_month, 1), "
                "    end_date = (make_date(year, end_month, 1) + interval '1 month' - interval '1 day')::date "
                "WHERE start_date IS NULL"
            ))
            await session.execute(sa_text(
                "ALTER TABLE admission_calendar ALTER COLUMN start_date SET NOT NULL"
            ))
            await session.execute(sa_text(
                "ALTER TABLE admission_calendar ALTER COLUMN end_date SET NOT NULL"
            ))
            await session.execute(sa_text("ALTER TABLE admission_calendar DROP COLUMN start_month"))
            await session.execute(sa_text("ALTER TABLE admission_calendar DROP COLUMN end_month"))
            changed = True

        # --- Phase 2: ensure year column exists ---
        # Re-check columns after phase 1
        if changed:
            result = await session.execute(sa_text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name = 'admission_calendar'"
            ))
            columns = {row[0] for row in result.all()}

        if "year" not in columns and "start_date" in columns:
            await session.execute(sa_text(
                "ALTER TABLE admission_calendar ADD COLUMN year INTEGER"
            ))
            await session.execute(sa_text(
                "UPDATE admission_calendar SET year = EXTRACT(YEAR FROM start_date)::int"
            ))
            await session.execute(sa_text(
                "ALTER TABLE admission_calendar ALTER COLUMN year SET NOT NULL"
            ))
            changed = True

        if changed:
            await session.commit()


async def seed_calendar_periods() -> None:
    """Seed default calendar periods if none exist."""
    await _migrate_calendar_columns()

    session_factory = get_session_factory()
    async with session_factory() as session:
        count_result = await session.execute(select(func.count()).select_from(AdmissionCalendar))
        count = count_result.scalar() or 0
        if count > 0:
            return

        for period in CALENDAR_PERIODS:
            session.add(AdmissionCalendar(**period))

        await session.commit()


async def seed_model_config() -> None:
    """Seed model config from env vars if DB tables are empty (first-boot migration)."""
    from app.models.model_config import ModelEndpoint, ModelGroup, ModelInstance

    session_factory = get_session_factory()
    async with session_factory() as session:
        ep_count = await session.execute(select(func.count()).select_from(ModelEndpoint))
        if (ep_count.scalar() or 0) > 0:
            return

        from app.config import settings

        if not settings.LLM_PRIMARY_API_KEY and not settings.LLM_PRIMARY_BASE_URL:
            return

        primary_ep = ModelEndpoint(
            name="主接入点",
            provider=settings.LLM_PRIMARY_PROVIDER or "qwen",
            base_url=settings.LLM_PRIMARY_BASE_URL,
            api_key=settings.LLM_PRIMARY_API_KEY,
        )
        session.add(primary_ep)
        await session.flush()

        if settings.LLM_PRIMARY_MODEL:
            llm_group = ModelGroup(name="默认LLM", type="llm", strategy="failover", enabled=True, priority=0)
            session.add(llm_group)
            await session.flush()
            session.add(ModelInstance(
                group_id=llm_group.id, endpoint_id=primary_ep.id,
                model_name=settings.LLM_PRIMARY_MODEL,
                enabled=True, weight=1, max_tokens=4096, temperature=0.7, priority=0,
            ))

        if settings.LLM_REVIEW_MODEL:
            review_ep = primary_ep
            if settings.LLM_REVIEW_BASE_URL and settings.LLM_REVIEW_BASE_URL != settings.LLM_PRIMARY_BASE_URL:
                review_ep = ModelEndpoint(
                    name="审核接入点",
                    provider=settings.LLM_REVIEW_PROVIDER or settings.LLM_PRIMARY_PROVIDER or "qwen",
                    base_url=settings.LLM_REVIEW_BASE_URL,
                    api_key=settings.LLM_PRIMARY_API_KEY,
                )
                session.add(review_ep)
                await session.flush()

            review_group = ModelGroup(name="默认审核", type="review", strategy="failover", enabled=True, priority=0)
            session.add(review_group)
            await session.flush()
            session.add(ModelInstance(
                group_id=review_group.id, endpoint_id=review_ep.id,
                model_name=settings.LLM_REVIEW_MODEL,
                enabled=True, weight=1, max_tokens=2048, temperature=0.3, priority=0,
            ))

        emb_base = settings.EMBEDDING_BASE_URL or settings.LLM_PRIMARY_BASE_URL
        emb_key = settings.EMBEDDING_API_KEY or settings.LLM_PRIMARY_API_KEY
        if settings.EMBEDDING_MODEL and emb_base:
            if emb_base == settings.LLM_PRIMARY_BASE_URL and emb_key == settings.LLM_PRIMARY_API_KEY:
                emb_ep = primary_ep
            else:
                emb_ep = ModelEndpoint(
                    name="Embedding接入点", provider="openai_compatible",
                    base_url=emb_base, api_key=emb_key,
                )
                session.add(emb_ep)
                await session.flush()

            emb_group = ModelGroup(name="默认Embedding", type="embedding", strategy="failover", enabled=True, priority=0)
            session.add(emb_group)
            await session.flush()
            session.add(ModelInstance(
                group_id=emb_group.id, endpoint_id=emb_ep.id,
                model_name=settings.EMBEDDING_MODEL,
                enabled=True, weight=1, max_tokens=8192, temperature=0.0, priority=0,
            ))

        await session.commit()


async def seed_system_configs() -> None:
    """Seed default system configs when missing."""
    from app.services.system_config_service import (
        CHAT_GUARDRAIL_CONFIG_KEY,
        DEFAULT_CHAT_GUARDRAIL_CONFIG,
        SYSTEM_BASIC_CONFIG_KEY,
        DEFAULT_SYSTEM_BASIC_CONFIG,
    )

    session_factory = get_session_factory()
    async with session_factory() as session:
        result = await session.execute(select(SystemConfig).where(SystemConfig.key == CHAT_GUARDRAIL_CONFIG_KEY))
        if result.scalar_one_or_none() is None:
            session.add(SystemConfig(
                key=CHAT_GUARDRAIL_CONFIG_KEY,
                value=DEFAULT_CHAT_GUARDRAIL_CONFIG,
                description="聊天风险判定与分级提示词配置",
            ))

        result = await session.execute(select(SystemConfig).where(SystemConfig.key == SYSTEM_BASIC_CONFIG_KEY))
        if result.scalar_one_or_none() is None:
            session.add(SystemConfig(
                key=SYSTEM_BASIC_CONFIG_KEY,
                value=DEFAULT_SYSTEM_BASIC_CONFIG,
                description="系统名称与Logo配置",
            ))
        await session.commit()


# Default workflow templates with state-machine definitions
DEFAULT_WORKFLOWS = [
    {
        "name": "单级审核",
        "code": "single",
        "definition": {
            "nodes": [
                {"id": "pending", "name": "待审核", "type": "start", "view_roles": ["reviewer", "admin", "super_admin"], "edit_roles": ["reviewer", "admin", "super_admin"]},
                {"id": "approved", "name": "已通过", "type": "terminal", "view_roles": ["reviewer", "admin", "super_admin"], "edit_roles": []},
                {"id": "rejected", "name": "不通过", "type": "terminal", "view_roles": ["reviewer", "admin", "super_admin"], "edit_roles": []},
            ],
            "actions": [
                {"id": "approve", "name": "通过"},
                {"id": "reject", "name": "拒绝"},
            ],
            "transitions": [
                {"from_node": "pending", "action": "approve", "to_node": "approved"},
                {"from_node": "pending", "action": "reject", "to_node": "rejected"},
            ],
        },
        "steps": [{"step": 1, "name": "审核", "role_code": "reviewer"}],
        "is_system": True,
    },
    {
        "name": "双级审核",
        "code": "double",
        "definition": {
            "nodes": [
                {"id": "pending", "name": "待审核", "type": "start", "view_roles": ["reviewer", "admin", "super_admin"], "edit_roles": ["reviewer", "super_admin"]},
                {"id": "reviewing", "name": "复审中", "type": "intermediate", "view_roles": ["admin", "super_admin"], "edit_roles": ["admin", "super_admin"]},
                {"id": "approved", "name": "已通过", "type": "terminal", "view_roles": ["reviewer", "admin", "super_admin"], "edit_roles": []},
                {"id": "rejected", "name": "不通过", "type": "terminal", "view_roles": ["reviewer", "admin", "super_admin"], "edit_roles": []},
            ],
            "actions": [
                {"id": "approve", "name": "通过"},
                {"id": "reject", "name": "拒绝"},
            ],
            "transitions": [
                {"from_node": "pending", "action": "approve", "to_node": "reviewing"},
                {"from_node": "pending", "action": "reject", "to_node": "rejected"},
                {"from_node": "reviewing", "action": "approve", "to_node": "approved"},
                {"from_node": "reviewing", "action": "reject", "to_node": "rejected"},
            ],
        },
        "steps": [
            {"step": 1, "name": "初审", "role_code": "reviewer"},
            {"step": 2, "name": "终审", "role_code": "admin"},
        ],
        "is_system": True,
    },
]

DEFAULT_BINDINGS = [
    {"resource_type": "knowledge", "workflow_code": "single"},
    {"resource_type": "media", "workflow_code": "single"},
]


async def seed_review_workflows() -> None:
    """Seed default review workflow templates and bindings."""
    session_factory = get_session_factory()
    async with session_factory() as session:
        wf_result = await session.execute(select(ReviewWorkflow))
        existing_wf = {w.code: w for w in wf_result.scalars().all()}

        for wf_data in DEFAULT_WORKFLOWS:
            if wf_data["code"] not in existing_wf:
                wf = ReviewWorkflow(**wf_data)
                session.add(wf)
                existing_wf[wf_data["code"]] = wf
            else:
                # Update existing workflow with definition if missing
                existing = existing_wf[wf_data["code"]]
                if not existing.definition and wf_data.get("definition"):
                    existing.definition = wf_data["definition"]

        await session.flush()

        bind_result = await session.execute(select(ResourceWorkflowBinding))
        existing_bindings = {b.resource_type: b for b in bind_result.scalars().all()}

        for bind_data in DEFAULT_BINDINGS:
            if bind_data["resource_type"] not in existing_bindings:
                wf = existing_wf.get(bind_data["workflow_code"])
                if wf:
                    binding = ResourceWorkflowBinding(
                        resource_type=bind_data["resource_type"],
                        workflow_id=wf.id,
                        enabled=True,
                    )
                    session.add(binding)

        await session.commit()


async def seed_default_knowledge_base():
    """Ensure a default knowledge base exists and all orphan documents are assigned to it."""
    from app.models.knowledge import KnowledgeBase, KnowledgeDocument

    session_factory = get_session_factory()
    async with session_factory() as db:
        count = (await db.execute(select(func.count()).select_from(KnowledgeBase))).scalar() or 0
        if count == 0:
            default_kb = KnowledgeBase(
                name="默认知识库",
                description="系统默认知识库",
                enabled=True,
                sort_order=0,
            )
            db.add(default_kb)
            await db.flush()

            from sqlalchemy import update
            await db.execute(
                update(KnowledgeDocument)
                .where(KnowledgeDocument.kb_id.is_(None))
                .values(kb_id=default_kb.id)
            )
            await db.commit()
        else:
            first_kb = (await db.execute(
                select(KnowledgeBase).order_by(KnowledgeBase.sort_order, KnowledgeBase.created_at).limit(1)
            )).scalar_one_or_none()
            if first_kb:
                orphan_count = (await db.execute(
                    select(func.count()).select_from(KnowledgeDocument)
                    .where(KnowledgeDocument.kb_id.is_(None))
                )).scalar() or 0
                if orphan_count > 0:
                    from sqlalchemy import update
                    await db.execute(
                        update(KnowledgeDocument)
                        .where(KnowledgeDocument.kb_id.is_(None))
                        .values(kb_id=first_kb.id)
                    )
                    await db.commit()
