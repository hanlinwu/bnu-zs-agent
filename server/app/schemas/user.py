"""Pydantic schemas for user authentication."""

from pydantic import BaseModel, Field
import re


class SmsSendRequest(BaseModel):
    phone: str = Field(..., pattern=r"^1[3-9]\d{9}$", description="中国手机号")


class SmsSendResponse(BaseModel):
    success: bool
    message: str


class LoginRequest(BaseModel):
    phone: str = Field(..., pattern=r"^1[3-9]\d{9}$")
    code: str = Field(..., min_length=6, max_length=6)
    nickname: str | None = Field(None, max_length=50)
    user_role: str | None = Field(None, description="gaokao/kaoyan/international/parent")


class LoginResponse(BaseModel):
    success: bool
    token: str | None = None
    message: str | None = None
    user: dict | None = None


class UserInfoResponse(BaseModel):
    id: str
    phone: str
    nickname: str
    avatar_url: str
    gender: str | None
    province: str | None
    birth_year: int | None
    school: str | None
    status: str


class UserUpdateRequest(BaseModel):
    nickname: str | None = Field(None, max_length=50)
    avatar_url: str | None = Field(None, max_length=500)
    gender: str | None = Field(None, pattern=r"^(male|female|unknown)$")
    province: str | None = Field(None, max_length=20)
    birth_year: int | None = None
    school: str | None = Field(None, max_length=100)
