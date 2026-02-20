"""Pydantic schemas for knowledge management."""

from pydantic import BaseModel, Field, model_validator


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


class CrawlTaskCreateRequest(BaseModel):
    kbId: str
    startUrl: str = Field(..., max_length=1000)
    maxDepth: int = Field(2, ge=0, le=10)
    maxPages: int | None = Field(None, ge=1, le=200)
    sameDomainOnly: bool = True

    @model_validator(mode="after")
    def compat_max_pages(self):
        # Backward compatibility for old frontend payloads.
        if self.maxPages is not None and self.maxDepth == 2:
            self.maxDepth = min(10, max(0, self.maxPages // 10))
        return self


class CrawlTaskResponse(BaseModel):
    id: str
    kbId: str
    startUrl: str
    maxDepth: int
    sameDomainOnly: bool
    status: str
    progress: int
    totalPages: int
    successPages: int
    failedPages: int
    currentUrl: str | None = None
    errorMessage: str | None = None
    resultDocumentIds: list[str] = []
    createdBy: str
    startedAt: str | None = None
    finishedAt: str | None = None
    createdAt: str
    updatedAt: str


class CrawlTaskListResponse(BaseModel):
    items: list[CrawlTaskResponse]
    total: int
    page: int
    pageSize: int
