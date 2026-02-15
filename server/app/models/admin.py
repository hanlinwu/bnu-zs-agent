import uuid
from datetime import datetime

from sqlalchemy import String, ForeignKey, DateTime, text
from sqlalchemy.dialects.postgresql import UUID, INET
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AdminUser(Base):
    __tablename__ = "admin_users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    real_name: Mapped[str] = mapped_column(String(50), nullable=False)
    employee_id: Mapped[str | None] = mapped_column(String(30), unique=True)
    department: Mapped[str | None] = mapped_column(String(100))
    title: Mapped[str | None] = mapped_column(String(50))
    phone: Mapped[str | None] = mapped_column(String(11))
    email: Mapped[str | None] = mapped_column(String(100))
    avatar_url: Mapped[str] = mapped_column(String(500), default="")
    mfa_secret: Mapped[str | None] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(String(10), nullable=False, default="active")
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_login_ip: Mapped[str | None] = mapped_column(INET)
    token_expire_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("admin_users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("NOW()"))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("NOW()"))
