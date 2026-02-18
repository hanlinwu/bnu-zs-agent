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
    embeddingModel: str | None = None
    embeddingStatus: str = "missing"


class ChunkDetailResponse(BaseModel):
    id: str
    chunkIndex: int
    content: str
    tokenCount: int | None
    embeddingModel: str | None = None
    embeddingStatus: str = "missing"
    embeddingVector: str | None = None


class ChunkListResponse(BaseModel):
    items: list[ChunkPreviewResponse]
    total: int
    page: int
    pageSize: int


class ReembedRequest(BaseModel):
    documentId: str | None = None
    limit: int = Field(2000, ge=1, le=20000)


class ReembedResponse(BaseModel):
    success: bool
    updated: int
    scanned: int
    message: str
