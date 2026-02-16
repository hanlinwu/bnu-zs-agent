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
    },
    "admin": {
        "knowledge": ["read", "create"],
        "user": ["read"],
        "model": ["read"],
        "log": ["read"],
        "media": ["read", "create"],
        "sensitive": ["read"],
        "calendar": ["read"],
        "dashboard": ["read"],
    },
    "teacher": {
        "knowledge": ["read"],
        "user": ["read"],
        "media": ["read"],
        "calendar": ["read"],
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


# Default calendar periods
CALENDAR_PERIODS = [
    {"period_name": "备考期", "start_month": 1, "end_month": 5, "year": 2026, "tone_config": {"style": "motivational", "description": "激励、备考建议、专业前景", "keywords": ["高考加油", "备考建议", "专业介绍"]}, "is_active": True},
    {"period_name": "高考后/报名期", "start_month": 6, "end_month": 7, "year": 2026, "tone_config": {"style": "guidance", "description": "志愿填报、分数线预测、报名指南", "keywords": ["志愿填报", "分数线", "报名指南"]}, "is_active": True},
    {"period_name": "录取查询期", "start_month": 8, "end_month": 9, "year": 2026, "tone_config": {"style": "enrollment", "description": "录取结果查询、入学准备清单", "keywords": ["录取查询", "入学准备", "报到须知"]}, "is_active": True},
    {"period_name": "常态期", "start_month": 10, "end_month": 12, "year": 2026, "tone_config": {"style": "general", "description": "校园文化、师资力量、国际交流", "keywords": ["校园文化", "师资力量", "国际交流"]}, "is_active": True},
]


async def seed_calendar_periods() -> None:
    """Seed default calendar periods if none exist."""
    session_factory = get_session_factory()
    async with session_factory() as session:
        count_result = await session.execute(select(func.count()).select_from(AdmissionCalendar))
        count = count_result.scalar() or 0
        if count > 0:
            return

        for period in CALENDAR_PERIODS:
            session.add(AdmissionCalendar(**period))

        await session.commit()
