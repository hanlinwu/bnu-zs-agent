"""Pydantic schemas for model configuration CRUD."""

from pydantic import BaseModel, Field


# ─── Endpoint ────────────────────────────────────────────────────

class EndpointCreate(BaseModel):
    name: str
    provider: str = "openai_compatible"
    baseUrl: str = Field(alias="baseUrl")
    apiKey: str = Field(default="", alias="apiKey")

    model_config = {"populate_by_name": True}


class EndpointUpdate(BaseModel):
    name: str | None = None
    provider: str | None = None
    baseUrl: str | None = Field(default=None, alias="baseUrl")
    apiKey: str | None = Field(default=None, alias="apiKey")

    model_config = {"populate_by_name": True}


class EndpointResponse(BaseModel):
    id: str
    name: str
    provider: str
    baseUrl: str
    apiKey: str  # masked
    createdAt: str

    model_config = {"populate_by_name": True}


# ─── Instance ────────────────────────────────────────────────────

class InstanceCreate(BaseModel):
    endpointId: str = Field(alias="endpointId")
    modelName: str = Field(alias="modelName")
    enabled: bool = True
    weight: int = 1
    maxTokens: int = Field(default=4096, alias="maxTokens")
    temperature: float = 0.7
    priority: int = 0

    model_config = {"populate_by_name": True}


class InstanceUpdate(BaseModel):
    endpointId: str | None = Field(default=None, alias="endpointId")
    modelName: str | None = Field(default=None, alias="modelName")
    enabled: bool | None = None
    weight: int | None = None
    maxTokens: int | None = Field(default=None, alias="maxTokens")
    temperature: float | None = None
    priority: int | None = None

    model_config = {"populate_by_name": True}


class InstanceResponse(BaseModel):
    id: str
    groupId: str
    endpointId: str
    modelName: str
    enabled: bool
    weight: int
    maxTokens: int
    temperature: float
    priority: int
    createdAt: str
    endpoint: EndpointResponse | None = None

    model_config = {"populate_by_name": True}


# ─── Group ───────────────────────────────────────────────────────

class GroupCreate(BaseModel):
    name: str
    type: str  # llm | embedding | review
    strategy: str = "failover"
    enabled: bool = True
    priority: int = 0

    model_config = {"populate_by_name": True}


class GroupUpdate(BaseModel):
    name: str | None = None
    strategy: str | None = None
    enabled: bool | None = None
    priority: int | None = None

    model_config = {"populate_by_name": True}


class GroupResponse(BaseModel):
    id: str
    name: str
    type: str
    strategy: str
    enabled: bool
    priority: int
    createdAt: str
    instances: list[InstanceResponse] = []

    model_config = {"populate_by_name": True}


# ─── Overview ────────────────────────────────────────────────────

class ModelConfigOverview(BaseModel):
    endpoints: list[EndpointResponse] = []
    groups: list[GroupResponse] = []

    model_config = {"populate_by_name": True}


# ─── Test requests (kept from original) ─────────────────────────

class ModelTestRequest(BaseModel):
    provider: str
    api_key: str
    base_url: str
    model: str


class EmbeddingTestRequest(BaseModel):
    api_key: str
    base_url: str
    model: str
