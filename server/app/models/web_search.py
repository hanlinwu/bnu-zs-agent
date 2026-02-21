"""Web search site configuration model."""

import uuid
from datetime import datetime

from sqlalchemy import String, Integer, Text, DateTime, Boolean, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class WebSearchSite(Base):
    __tablename__ = "web_search_sites"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    domain: Mapped[str] = mapped_column(String(500), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    start_url: Mapped[str] = mapped_column(String(1000), nullable=False)
    max_depth: Mapped[int] = mapped_column(
        Integer, nullable=False, default=3, server_default=text("3")
    )
    max_pages: Mapped[int] = mapped_column(
        Integer, nullable=False, default=100, server_default=text("100")
    )
    same_domain_only: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=text("true")
    )
    crawl_frequency_minutes: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1440, server_default=text("1440")
    )
    enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=text("true")
    )
    # ID of this site in the search microservice's SQLite DB
    remote_site_id: Mapped[str | None] = mapped_column(String(100))
    last_crawl_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_crawl_status: Mapped[str | None] = mapped_column(String(20))
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("NOW()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("NOW()")
    )
