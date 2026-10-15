"""通用响应结构。"""
from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    """统一响应外壳（前端只需处理一种结构）。"""

    success: bool = True
    code: str = "OK"
    message: str = "操作成功"
    data: T | None = None


class PageMeta(BaseModel):
    total: int = 0
    page: int = 1
    page_size: int = 20
    pages: int = 0


class Page(BaseModel, Generic[T]):
    items: list[T] = Field(default_factory=list)
    meta: PageMeta = Field(default_factory=PageMeta)


class ErrorResponse(BaseModel):
    success: bool = False
    code: str = "APP_ERROR"
    message: str = "请求失败"
    detail: object | None = None


class HealthOut(BaseModel):
    status: str = "ok"
    app_name: str
    env: str
    vector_backend: str
    vector_backend_ready: bool
    face_engine: str
    engine_ready: bool
    cosine_threshold: float
    confidence_floor: float
    person_count: int
    face_count: int
    log_count: int
