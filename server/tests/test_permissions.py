"""Tests for RBAC permission checking."""

from app.core.exceptions import ForbiddenError


def test_forbidden_error_has_correct_status():
    err = ForbiddenError("测试权限不足")
    assert err.status_code == 403
    assert err.detail["message"] == "测试权限不足"


def test_permission_module_imports():
    from app.core.permissions import require_permission, get_admin_permissions, invalidate_admin_permissions
    assert callable(require_permission)
    assert callable(get_admin_permissions)
    assert callable(invalidate_admin_permissions)


def test_require_permission_returns_callable():
    from app.core.permissions import require_permission
    checker = require_permission("knowledge:create")
    assert callable(checker)
