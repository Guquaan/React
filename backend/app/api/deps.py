"""FastAPI 依赖注入。

所有 service 都通过这里构造，路由函数里不出现任何 Session/仓储/引擎的 new 操作，
这样替换实现（比如把 Chroma 换成 Milvus）不需要改一行路由代码。
"""
from __future__ import annotations

from collections.abc import Iterator

from fastapi import Depends, File, UploadFile
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.errors import ValidationError
from app.db import get_db
from app.services import (
    FaceService,
    PersonService,
    QrCodeService,
    RecognitionService,
    StatsService,
)


def settings_dep() -> Settings:
    return get_settings()


def person_service(db: Session = Depends(get_db)) -> PersonService:
    return PersonService(db)


def face_service(db: Session = Depends(get_db)) -> FaceService:
    return FaceService(db)


def recognition_service(db: Session = Depends(get_db)) -> RecognitionService:
    return RecognitionService(db)


def qrcode_service(db: Session = Depends(get_db)) -> QrCodeService:
    return QrCodeService(db)


def stats_service(db: Session = Depends(get_db)) -> StatsService:
    return StatsService(db)


# ----------------------------------------------------------------------
async def read_image_upload(file: UploadFile = File(...)) -> tuple[str, bytes]:
    """读取单张上传图片并校验大小。"""
    return await _read(file, get_settings())


async def read_image_uploads(
    files: list[UploadFile] = File(...),
) -> list[tuple[str, bytes]]:
    """读取多张上传图片（用于多角度注册）。"""
    if not files:
        raise ValidationError("请至少上传一张图片")
    s = get_settings()
    return [await _read(f, s) for f in files]


async def _read(file: UploadFile, s: Settings) -> tuple[str, bytes]:
    data = await file.read()
    if not data:
        raise ValidationError(f"文件为空: {file.filename}")
    limit = s.max_upload_mb * 1024 * 1024
    if len(data) > limit:
        raise ValidationError(f"图片过大（{len(data) / 1024 / 1024:.1f}MB），上限 {s.max_upload_mb}MB")
    return (file.filename or "upload.jpg", data)


__all__ = [
    "Depends",
    "face_service",
    "person_service",
    "qrcode_service",
    "read_image_upload",
    "read_image_uploads",
    "recognition_service",
    "settings_dep",
    "stats_service",
]
