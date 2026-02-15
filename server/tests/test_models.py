from app.models.user import User
from app.models.admin import AdminUser


def test_user_model_has_required_fields():
    """验证 User 模型具有设计文档中定义的所有字段"""
    columns = {c.name for c in User.__table__.columns}
    required = {
        "id", "phone", "nickname", "avatar_url", "gender", "province",
        "birth_year", "school", "status", "last_login_at", "last_login_ip",
        "token_expire_at", "created_at", "updated_at",
    }
    assert required.issubset(columns)


def test_admin_user_model_has_required_fields():
    """验证 AdminUser 模型具有设计文档中定义的所有字段"""
    columns = {c.name for c in AdminUser.__table__.columns}
    required = {
        "id", "username", "password_hash", "real_name", "employee_id",
        "department", "title", "phone", "email", "avatar_url", "mfa_secret",
        "status", "last_login_at", "last_login_ip", "token_expire_at",
        "created_by", "created_at", "updated_at",
    }
    assert required.issubset(columns)


def test_rbac_tables_exist():
    """验证 RBAC 5 表模型存在且表名正确"""
    from app.models.role import Role, Permission, RolePermission, UserRole, AdminRole
    assert Role.__tablename__ == "roles"
    assert Permission.__tablename__ == "permissions"
    assert RolePermission.__tablename__ == "role_permissions"
    assert UserRole.__tablename__ == "user_roles"
    assert AdminRole.__tablename__ == "admin_roles"
