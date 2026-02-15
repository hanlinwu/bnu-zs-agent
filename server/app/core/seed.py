"""Seed data for RBAC roles, permissions, and default super admin."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session_factory
from app.models.role import Role, Permission, RolePermission, AdminRole
from app.models.admin import AdminUser

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

# 7 resources × 6 actions
RESOURCES = ["knowledge", "user", "model", "log", "media", "sensitive_word", "calendar"]
ACTIONS = ["create", "read", "update", "delete", "approve", "export"]

# Permission matrix per admin role
ROLE_PERMISSIONS = {
    "super_admin": {r: ACTIONS for r in RESOURCES},  # all permissions
    "reviewer": {
        "knowledge": ["read", "approve"],
        "user": ["read"],
        "media": ["read", "approve"],
        "sensitive_word": ["read"],
        "log": ["read"],
    },
    "admin": {
        "knowledge": ["read", "create"],
        "user": ["read"],
        "model": ["read"],
        "log": ["read"],
        "media": ["read", "create"],
        "sensitive_word": ["read"],
        "calendar": ["read"],
    },
    "teacher": {
        "knowledge": ["read"],
        "user": ["read"],
        "media": ["read"],
        "calendar": ["read"],
    },
}


async def seed_roles_and_permissions() -> None:
    """Insert preset roles, permissions, and default admin if not exists."""
    session_factory = get_session_factory()
    async with session_factory() as session:
        # Check if already seeded
        result = await session.execute(select(Role).limit(1))
        if result.scalar_one_or_none() is not None:
            return

        # Create roles
        role_map: dict[str, Role] = {}
        for role_data in ROLES:
            role = Role(**role_data)
            session.add(role)
            role_map[role_data["code"]] = role

        # Create permissions
        perm_map: dict[str, Permission] = {}
        for resource in RESOURCES:
            for action in ACTIONS:
                code = f"{resource}:{action}"
                perm = Permission(
                    code=code,
                    name=f"{resource} {action}",
                    resource=resource,
                    action=action,
                )
                session.add(perm)
                perm_map[code] = perm

        await session.flush()

        # Create role-permission associations
        for role_code, resource_actions in ROLE_PERMISSIONS.items():
            role = role_map[role_code]
            for resource, actions in resource_actions.items():
                for action in actions:
                    perm_code = f"{resource}:{action}"
                    rp = RolePermission(role_id=role.id, permission_id=perm_map[perm_code].id)
                    session.add(rp)

        # Create default super admin (password: admin123, must change on first login)
        from app.core.security import hash_password
        default_admin = AdminUser(
            username="admin",
            password_hash=hash_password("admin123"),
            real_name="系统管理员",
            status="active",
        )
        session.add(default_admin)
        await session.flush()

        # Assign super_admin role to default admin
        admin_role = AdminRole(
            admin_id=default_admin.id,
            role_id=role_map["super_admin"].id,
        )
        session.add(admin_role)

        await session.commit()
