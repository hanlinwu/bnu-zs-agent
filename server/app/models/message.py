import uuid
from datetime import datetime

from sqlalchemy import String, Boolean, Text, ForeignKey, DateTime, Index, text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Message(Base):
    __tablename__ = "messages"
    __table_args__ = (
        Index("idx_msg_conv", "conversation_id", "created_at", postgresql_where=text("is_deleted = FALSE")),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    conversation_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False)
    role: Mapped[str] = mapped_column(String(10), nullable=False)  # user / assistant / system
    content: Mapped[str] = mapped_column(Text, nullable=False)
    model_version: Mapped[str | None] = mapped_column(String(50))
    risk_level: Mapped[str | None] = mapped_column(String(10))
    review_passed: Mapped[bool | None] = mapped_column(Boolean)
    sources: Mapped[dict | None] = mapped_column(JSONB)
    sensitive_words: Mapped[list[str] | None] = mapped_column(JSONB)  # 匹配的敏感词列表
    sensitive_level: Mapped[str | None] = mapped_column(String(10))  # block/warn/review
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("NOW()"))

    conversation = relationship("Conversation", back_populates="messages")
    media_associations = relationship("MessageMedia", back_populates="message", lazy="selectin")
