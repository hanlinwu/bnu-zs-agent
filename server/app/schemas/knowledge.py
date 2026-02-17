"""Pydantic schemas for knowledge management."""

from pydantic import BaseModel, Field


class KnowledgeDocResponse(BaseModel):
    id: str
    title: str
    fileType: str
    fileHash: str = ""
    fileSize: int = 0
    status: str
    currentNode: str = "pending"
    uploaderId: str
    uploaderName: str = ""
    reviewerId: str | None = None
    reviewerName: str | None = None
    reviewNote: str | None = None
    chunkCount: int = 0
    kbId: str | None = None
    createdAt: str
    updatedAt: str


class KnowledgeDocListResponse(BaseModel):
    items: list[KnowledgeDocResponse]
    total: int
    page: int
    pageSize: int


class KnowledgeReviewRequest(BaseModel):
    action: str = Field(..., max_length=50)
    note: str | None = Field(None, max_length=500)


class ChunkPreviewResponse(BaseModel):
    id: str
    chunkIndex: int
    content: str
    tokenCount: int | None


class ChunkListResponse(BaseModel):
    items: list[ChunkPreviewResponse]
    total: int
    page: int
    pageSize: int
