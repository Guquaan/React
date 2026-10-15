"""人脸注册 / 样本管理路由。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.api.deps import face_service, read_image_upload, read_image_uploads
from app.schemas.common import ApiResponse, Page
from app.schemas.face import DetectedFaceOut, FaceRegisterResult
from app.schemas.recognition import RecognitionLogOut
from app.services import FaceService

router = APIRouter(prefix="/faces", tags=["人脸注册"])


@router.post(
    "/persons/{person_id}/register",
    response_model=ApiResponse[FaceRegisterResult],
    summary="为指定人员注册人脸（支持一次上传多张不同角度）",
)
async def register_faces(
    person_id: str,
    uploads: list[tuple[str, bytes]] = Depends(read_image_uploads),
    make_first_primary: bool = Query(True, description="第一张是否设为主图"),
    svc: FaceService = Depends(face_service),
):
    result = svc.register_from_images(person_id, uploads, make_first_primary=make_first_primary)
    ok = result.accepted > 0
    return ApiResponse(
        success=True,
        data=result,
        message=f"注册完成：成功 {result.accepted} 张，拒绝 {result.rejected} 张" if ok else "全部图片都被拒绝，请检查照片质量",
    )


@router.post(
    "/persons/{person_id}/register-one",
    response_model=ApiResponse[FaceRegisterResult],
    summary="为指定人员注册人脸（单张）",
)
async def register_one_face(
    person_id: str,
    upload: tuple[str, bytes] = Depends(read_image_upload),
    svc: FaceService = Depends(face_service),
):
    result = svc.register_from_images(person_id, [upload])
    if result.accepted == 0:
        from app.core.errors import ValidationError

        raise ValidationError(result.messages[0] if result.messages else "注册失败")
    return ApiResponse(data=result, message="人脸注册成功")


@router.post(
    "/detect",
    response_model=ApiResponse[list[DetectedFaceOut]],
    summary="仅做人脸检测（预览用，不落库）",
)
async def detect_faces(
    upload: tuple[str, bytes] = Depends(read_image_upload),
    svc: FaceService = Depends(face_service),
):
    from app.core.errors import NoFaceDetectedError
    from app.utils.image import decode_image, resize_max

    image = resize_max(decode_image(upload[1]), 1280)
    faces = svc.engine.detect(image)
    if not faces:
        raise NoFaceDetectedError("未检测到人脸")
    return ApiResponse(
        data=[
            DetectedFaceOut(bbox=f.bbox, det_score=round(f.det_score, 4), quality_score=round(f.quality_score, 4))
            for f in faces
        ]
    )


@router.delete("/{face_id}", response_model=ApiResponse[dict], summary="删除某张人脸样本")
def delete_face(face_id: str, svc: FaceService = Depends(face_service)):
    svc.delete_face(face_id)
    return ApiResponse(data={"face_id": face_id}, message="人脸样本已删除")


@router.post("/sync-vectors", response_model=ApiResponse[dict], summary="矢量库与数据库对账，清理孤儿向量")
def sync_vectors(svc: FaceService = Depends(face_service)):
    return ApiResponse(data=svc.sync_vectors(), message="对账完成")
