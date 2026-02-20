"""Pydantic schemas for admin authentication."""

from pydantic import BaseModel, Field


class AdminLoginRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=50)
    password: str = Field(..., min_length=1)
    mfa_code: str | None = Field(None, min_length=6, max_length=6)
    sms_code: str | None = Field(None, min_length=6, max_length=6)


class AdminSmsSendRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=50)
    password: str = Field(..., min_length=1)


class AdminBindPhoneSendRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=50)
    password: str = Field(..., min_length=1)
    phone: str = Field(..., pattern=r"^1[3-9]\d{9}$")


class AdminBindPhoneConfirmRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=50)
    password: str = Field(..., min_length=1)
    phone: str = Field(..., pattern=r"^1[3-9]\d{9}$")
    sms_code: str = Field(..., min_length=6, max_length=6)
    mfa_code: str | None = Field(None, min_length=6, max_length=6)


class AdminLoginResponse(BaseModel):
    success: bool
    token: str | None = None
    message: str | None = None
    admin: dict | None = None


class AdminInfoResponse(BaseModel):
    id: str
    username: str
    real_name: str
    employee_id: str | None
    department: str | None
    title: str | None
    phone: str | None
    email: str | None
    avatar_url: str
    status: str
    permissions: list[str]
