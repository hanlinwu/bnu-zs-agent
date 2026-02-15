"""Unified exception classes for the application."""

from fastapi import HTTPException


class BizError(HTTPException):
    def __init__(self, code: int, message: str, status_code: int = 400):
        super().__init__(status_code=status_code, detail={"code": code, "message": message})


class UnauthorizedError(BizError):
    def __init__(self, message: str = "未授权"):
        super().__init__(code=401, message=message, status_code=401)


class ForbiddenError(BizError):
    def __init__(self, message: str = "无权限"):
        super().__init__(code=403, message=message, status_code=403)


class NotFoundError(BizError):
    def __init__(self, message: str = "资源不存在"):
        super().__init__(code=404, message=message, status_code=404)


class RateLimitError(BizError):
    def __init__(self, message: str = "请求过于频繁，请稍后再试"):
        super().__init__(code=429, message=message, status_code=429)
