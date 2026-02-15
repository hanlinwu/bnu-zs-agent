"""Pydantic schemas for knowledge management."""

from pydantic import BaseModel, Field


class KnowledgeDocResponse(BaseModel):
    id: str
    title: str
    file_type: str
    status: str
    uploaded_by: str
    reviewed_by: str | None = None
    review_note: str | None = None
    created_at: str
    updated_at: str


class KnowledgeDocListResponse(BaseModel):
    items: list[KnowledgeDocResponse]
    total: int
    page: int
    page_size: int


class KnowledgeReviewRequest(BaseModel):
    action: str = Field(..., pattern=r"^(approve|reject)$")
    note: str | None = Field(None, max_length=500)


class ChunkPreviewResponse(BaseModel):
    id: str
    chunk_index: int
    content: str
    token_count: int | None
