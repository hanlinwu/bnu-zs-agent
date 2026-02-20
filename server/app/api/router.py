"""API router — registers all v1 routes."""

from fastapi import APIRouter

from app.api.v1 import (
    auth,
    chat,
    conversation,
    knowledge,
    media,
    admin_auth,
    admin_admin,
    admin_user,
    admin_conversation,
    admin_role,
    admin_sensitive,
    admin_model,
    admin_calendar,
    admin_system_config,
    admin_log,
    admin_dashboard,
    admin_workflow,
    admin_knowledge_base,
    system,
)

api_router = APIRouter(prefix="/api/v1")

# User-facing routes
api_router.include_router(auth.router, prefix="/auth", tags=["用户认证"])
api_router.include_router(chat.router, prefix="/chat", tags=["智能对话"])
api_router.include_router(conversation.router, prefix="/conversations", tags=["对话管理"])
api_router.include_router(system.router, prefix="/system", tags=["系统信息"])

# Admin routes
api_router.include_router(admin_auth.router, prefix="/admin/auth", tags=["管理员认证"])
api_router.include_router(knowledge.router, prefix="/admin/knowledge", tags=["知识库管理"])
api_router.include_router(admin_knowledge_base.router, prefix="/admin/knowledge-bases", tags=["知识库"])
api_router.include_router(media.router, prefix="/admin/media", tags=["多媒体资源"])
api_router.include_router(admin_user.router, prefix="/admin/users", tags=["用户管理"])
api_router.include_router(admin_admin.router, prefix="/admin/admins", tags=["管理员管理"])
api_router.include_router(admin_role.router, prefix="/admin", tags=["角色权限"])
api_router.include_router(admin_sensitive.router, prefix="/admin/sensitive", tags=["敏感词库"])
api_router.include_router(admin_model.router, prefix="/admin/models", tags=["模型配置"])
api_router.include_router(admin_calendar.router, prefix="/admin/calendar", tags=["招生日历"])
api_router.include_router(admin_system_config.router, prefix="/admin/system-configs", tags=["系统配置"])
api_router.include_router(admin_log.router, prefix="/admin/logs", tags=["审计日志"])
api_router.include_router(admin_dashboard.router, prefix="/admin/dashboard", tags=["仪表盘"])
api_router.include_router(admin_conversation.router, prefix="/admin/conversations", tags=["对话审核"])
api_router.include_router(admin_workflow.router, prefix="/admin", tags=["审核流程"])
