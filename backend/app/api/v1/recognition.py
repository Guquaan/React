"""人脸识别路由：1:N 识别、1:1 比对、识别记录查询。"""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, Query

from app.api.deps import read_image_upload, recognition_service
from app.db import get_db
from app.repositories.log_repo import LogRepository
from app.schemas.common import ApiResponse, Page, PageMeta
from app.schemas.face import IdentifyResult, VerifyResult
from app.schemas.recognition import RecognitionLogDetail, RecognitionLogOut
from app.services import RecognitionService
from app.services.serializers import recognition_detail, recognition_out
from app.utils.image import decode_image
from sqlalchemy.orm import Session

router = APIRouter(prefix="/recognition", tags=["人脸识别"])


@router.post(
    "/identify",
    response_model=ApiResponse[IdentifyResult],
    summary="1:N 人脸识别（返回匹配人员、相似度、置信度与识别时间）",
)
async def identify(
    upload: tuple[str, bytes] = Depends(read_image_upload),
    top_k: int = Query(5, ge=1, le=20),
    source: str = Query("web"),
    svc: RecognitionService = Depends(recognition_service),
):
    result = svc.identify(decode_image(upload[1]), top_k=top_k, source=source)
    msg = (
        f"识别成功：{result.person.name}（置信度 {result.best.confidence:.1%}）"
        if result.matched and result.best and result.person
        else "未匹配到人员（最高置信度未达阈值）"
    )
    return ApiResponse(data=result, message=msg)


@router.post(
    "/identify-base64",
    response_model=ApiResponse[IdentifyResult],
    summary="1:N 人脸识别（base64 图片，供前端摄像头直接调用，避免 multipart 开销）",
)
async def identify_base64(
    body: dict,
    top_k: int = Query(5, ge=1, le=20),
    source: str = Query("camera"),
    svc: RecognitionService = Depends(recognition_service),
):
    import base64
    import binascii

    from app.core.errors import ValidationError

    raw = str(body.get("image") or "")
    if "," in raw and raw.strip().startswith("data:"):
        raw = raw.split(",", 1)[1]
    try:
        data = base64.b64decode(raw, validate=False)
    except (binascii.Error, ValueError) as exc:
        raise ValidationError(f"base64 图片解析失败: {exc}") from exc

    result = svc.identify(decode_image(data), top_k=top_k, source=source)
    msg = (
        f"识别成功：{result.person.name}（置信度 {result.best.confidence:.1%}）"
        if result.matched and result.best and result.person
        else "未匹配到人员（最高置信度未达阈值）"
    )
    return ApiResponse(data=result, message=msg)


@router.post(
    "/verify/{person_id}",
    response_model=ApiResponse[VerifyResult],
    summary="1:1 人脸比对（判断是否为该人员）",
)
async def verify(
    person_id: str,
    upload: tuple[str, bytes] = Depends(read_image_upload),
    source: str = Query("web"),
    svc: RecognitionService = Depends(recognition_service),
):
    result = svc.verify(person_id, decode_image(upload[1]), source=source)
    return ApiResponse(data=result, message=result.message)


@router.get(
    "/logs",
    response_model=ApiResponse[Page[RecognitionLogOut]],
    summary="识别记录（含时间、置信度、快照）",
)
def list_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    person_id: str | None = Query(None),
    is_matched: bool | None = Query(None),
    mode: str | None = Query(None, pattern="^(identify|verify)?$"),
    start: datetime | None = Query(None),
    end: datetime | None = Query(None),
    db: Session = Depends(get_db),
):
    rows, total = LogRepository(db).list_recognitions(
        page=page,
        page_size=page_size,
        person_id=person_id,
        is_matched=is_matched,
        mode=mode,
        start=start,
        end=end,
    )
    pages = (total + page_size - 1) // page_size
    return ApiResponse(
        data=Page[RecognitionLogOut](
            items=[recognition_out(r) for r in rows],
            meta=PageMeta(total=total, page=page, page_size=page_size, pages=pages),
        )
    )


@router.get(
    "/logs/{log_id}",
    response_model=ApiResponse[RecognitionLogDetail],
    summary="识别记录详情（含 TopK 候选）",
)
def get_log(log_id: str, db: Session = Depends(get_db)):
    from app.core.errors import NotFoundError
    from app.db.models import RecognitionLog
    from app.services.storage_service import get_storage

    row = db.get(RecognitionLog, log_id)
    if row is None:
        raise NotFoundError(f"识别记录不存在: {log_id}")

    person_img = None
    if row.person_id:
        from app.repositories.face_repo import FaceRepository

        primary = FaceRepository(db).primary_of(row.person_id)
        if primary:
            person_img = get_storage().to_url(primary.image_path)
    return ApiResponse(data=recognition_detail(row, person_image_url=person_img))
