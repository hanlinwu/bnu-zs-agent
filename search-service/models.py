"""Pydantic request/response schemas for the search microservice."""

from pydantic import BaseModel


# ── Crawl Sites ──────────────────────────────────────────────

class CrawlSiteCreate(BaseModel):
    domain: str
    name: str | None = None
    start_url: str
    max_depth: int = 3
    max_pages: int = 100
    same_domain_only: bool = True
    crawl_frequency_minutes: int = 1440
    enabled: bool = True


class CrawlSiteUpdate(BaseModel):
    name: str | None = None
    start_url: str | None = None
    max_depth: int | None = None
    max_pages: int | None = None
    same_domain_only: bool | None = None
    crawl_frequency_minutes: int | None = None
    enabled: bool | None = None


class CrawlSiteResponse(BaseModel):
    id: str
    domain: str
    name: str | None
    start_url: str
    max_depth: int
    max_pages: int
    same_domain_only: bool
    crawl_frequency_minutes: int
    enabled: bool
    last_crawl_at: str | None
    created_at: str
    updated_at: str


# ── Crawl Tasks ──────────────────────────────────────────────

class CrawlRequest(BaseModel):
    url: str
    domain_restriction: str | None = None
    max_depth: int = 3
    max_pages: int = 100
    same_domain_only: bool = True
    site_id: str | None = None


class CrawlTaskResponse(BaseModel):
    id: str
    site_id: str | None
    start_url: str
    status: str
    progress: int
    total_pages: int
    success_pages: int
    failed_pages: int
    error_message: str | None
    started_at: str | None
    finished_at: str | None
    created_at: str


# ── Search ───────────────────────────────────────────────────

class SearchRequest(BaseModel):
    query: str
    domain: str | None = None
    page: int = 1
    page_size: int = 20


class SearchHit(BaseModel):
    id: str
    url: str
    title: str
    content_snippet: str
    domain: str
    crawled_at: str
    score: float | None = None


class SearchResponse(BaseModel):
    hits: list[SearchHit]
    total: int
    query: str
    page: int
    page_size: int
