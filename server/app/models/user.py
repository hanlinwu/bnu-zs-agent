import uuid
from datetime import datetime

from sqlalchemy import String, Integer, DateTime, text
from sqlalchemy.dialects.postgresql import UUID, INET
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    phone: Mapped[str] = mapped_column(String(11), unique=True, nullable=False)
    nickname: Mapped[str] = mapped_column(String(50), nullable=False)
    avatar_url: Mapped[str] = mapped_column(String(500), default="")
    gender: Mapped[str | None] = mapped_column(String(10))
    province: Mapped[str | None] = mapped_column(String(20))
    birth_year: Mapped[int | None] = mapped_column(Integer)
    school: Mapped[str | None] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(String(10), nullable=False, default="active")
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_login_ip: Mapped[str | None] = mapped_column(INET)
    token_expire_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("NOW()"))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("NOW()"))
