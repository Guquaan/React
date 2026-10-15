"""统一异常体系。

业务层只抛 `AppError` 的子类，API 层统一捕获并转成 JSON 响应，
从而让 service / repository 层完全不感知 HTTP 的存在。
"""
from __future__ import annotations

from typing import Any


class AppError(Exception):
    """所有业务异常的基类。"""

    code: str = "APP_ERROR"
    http_status: int = 400

    def __init__(self, message: str, *, detail: Any = None) -> None:
        super().__init__(message)
        self.message = message
        self.detail = detail

    def to_dict(self) -> dict[str, Any]:
        return {"code": self.code, "message": self.message, "detail": self.detail}


class NotFoundError(AppError):
    code = "NOT_FOUND"
    http_status = 404


class ConflictError(AppError):
    code = "CONFLICT"
    http_status = 409


class ValidationError(AppError):
    code = "VALIDATION_ERROR"
    http_status = 422


class NoFaceDetectedError(AppError):
    """图片中没有检测到可用人脸。"""

    code = "NO_FACE_DETECTED"
    http_status = 422


class MultipleFacesError(AppError):
    """1:1 场景下要求图片里只有一张脸。"""

    code = "MULTIPLE_FACES"
    http_status = 422


class LowQualityFaceError(AppError):
    """人脸过小 / 过模糊，注册会拖低准确率。"""

    code = "LOW_QUALITY_FACE"
    http_status = 422


class VectorStoreError(AppError):
    code = "VECTOR_STORE_ERROR"
    http_status = 500


class TokenInvalidError(AppError):
    """二维码 token 校验失败或被篡改。"""

    code = "TOKEN_INVALID"
    http_status = 400
