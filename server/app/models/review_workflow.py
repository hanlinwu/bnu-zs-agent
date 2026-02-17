"""Review workflow models for configurable state-machine workflows."""

import uuid
from datetime import datetime

from sqlalchemy import String, Boolean, Integer, Text, ForeignKey, DateTime, text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ReviewWorkflow(Base):
    """工作流模板

    definition JSONB stores the full state-machine:
    {
        "nodes": [
            {"id": "pending", "name": "待审核", "type": "start", "view_roles": [...], "edit_roles": [...]},
            {"id": "approved", "name": "已通过", "type": "terminal", "view_roles": [...], "edit_roles": []},
            ...
        ],
        "actions": [
            {"id": "approve", "name": "通过"},
            {"id": "reject", "name": "拒绝"},
            ...
        ],
        "transitions": [
            {"from_node": "pending", "action": "approve", "to_node": "approved"},
            ...
        ]
    }

    Node types: start, intermediate, terminal
    """
    __tablename__ = "review_workflows"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    definition: Mapped[dict | None] = mapped_column(JSONB)
    # Deprecated: kept for backward compat during migration
    steps: Mapped[dict | None] = mapped_column(JSONB)
    is_system: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("NOW()"))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("NOW()"))


class ResourceWorkflowBinding(Base):
    """资源类型与工作流的绑定"""
    __tablename__ = "resource_workflow_bindings"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    resource_type: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    workflow_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("review_workflows.id"), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("NOW()"))


class ReviewRecord(Base):
    """审核记录（每次工作流动作的历史）"""
    __tablename__ = "review_records"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    resource_type: Mapped[str] = mapped_column(String(50), nullable=False)
    resource_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    from_node: Mapped[str | None] = mapped_column(String(50))
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    to_node: Mapped[str | None] = mapped_column(String(50))
    # Deprecated: kept for backward compat
    step: Mapped[int | None] = mapped_column(Integer)
    reviewer_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("admin_users.id"), nullable=False)
    note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("NOW()"))
