"""Pydantic schemas for chat and conversations."""

from pydantic import BaseModel, Field


class ConversationCreate(BaseModel):
    title: str | None = Field(None, max_length=200)


class ConversationUpdate(BaseModel):
    title: str | None = Field(None, max_length=200)
    is_pinned: bool | None = None


class ConversationResponse(BaseModel):
    id: str
    title: str | None
    is_pinned: bool
    created_at: str
    updated_at: str
    message_count: int = 0


class ConversationListResponse(BaseModel):
    items: list[ConversationResponse]
    total: int
    page: int
    page_size: int


class MessageResponse(BaseModel):
    id: str
    role: str
    content: str
    model_version: str | None = None
    risk_level: str | None = None
    review_passed: bool | None = None
    sources: list | None = None
    media_items: list | None = None
    created_at: str


class MessageListResponse(BaseModel):
    items: list[MessageResponse]
    total: int
    page: int
    page_size: int


class ChatSendRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=5000)
