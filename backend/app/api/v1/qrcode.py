"""二维码路由：生成人员二维码 / 扫码取数 / 扫码记录。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request, Response

from app.api.deps import qrcode_service
from app.core.errors import TokenInvalidError
from app.schemas.common import ApiResponse, Page, PageMeta
from app.schemas.recognition import QrPayloadOut, QrResolveOut, QrScanLogOut
from app.services import QrCodeService
from app.services.serializers import qr_scan_out

router = APIRouter(prefix="/qrcode", tags=["二维码取数"])


@router.get("/persons/{person_id}.png", summary="获取人员二维码图片（PNG）")
def person_qrcode(
    person_id: str,
    box_size: int = Query(10, ge=2, le=30),
    svc: QrCodeService = Depends(qrcode_service),
):
    png, payload = svc.person_qrcode_png(person_id)
    return Response(
        content=png,
        media_type="image/png",
        headers={
            "Cache-Control": "no-store",
            "X-Person-Code": payload.person_code,
            "Content-Disposition": f'inline; filename="qrcode_{payload.person_code}.png"',
        },
    )


@router.get("/persons/{person_id}/payload", response_model=ApiResponse[QrPayloadOut], summary="获取人员二维码内容（JSON）")
def person_qrcode_payload(person_id: str, svc: QrCodeService = Depends(qrcode_service)):
    return ApiResponse(data=svc.build_payload_by_id(person_id))


@router.get("/resolve", response_model=ApiResponse[QrResolveOut], summary="扫码解析：用 token 换取人员完整数据")
def resolve(
    request: Request,
    token: str = Query(..., description="二维码中的签名 token"),
    svc: QrCodeService = Depends(qrcode_service),
):
    client_ip = request.client.host if request.client else None
    data = svc.resolve(
        token,
        client_ip=client_ip,
        user_agent=request.headers.get("user-agent"),
    )
    return ApiResponse(data=data, message=data.message)


@router.get("/parse", response_model=ApiResponse[QrResolveOut], summary="扫码解析（可直接粘贴二维码里的完整链接）")
def parse_url(
    request: Request,
    url: str = Query(..., description="完整扫码链接或 token"),
    svc: QrCodeService = Depends(qrcode_service),
):
    token = url.split("token=", 1)[1] if "token=" in url else url
    token = token.split("&", 1)[0]
    client_ip = request.client.host if request.client else None
    try:
        data = svc.resolve(token, client_ip=client_ip, user_agent=request.headers.get("user-agent"))
    except TokenInvalidError as exc:
        raise exc
    return ApiResponse(data=data, message=data.message)


@router.get("/scans", response_model=ApiResponse[Page[QrScanLogOut]], summary="扫码记录（审计）")
def list_scans(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    svc: QrCodeService = Depends(qrcode_service),
):
    rows, total = svc.list_scans(page=page, page_size=page_size)
    pages = (total + page_size - 1) // page_size
    return ApiResponse(
        data=Page[QrScanLogOut](
            items=[qr_scan_out(r) for r in rows],
            meta=PageMeta(total=total, page=page, page_size=page_size, pages=pages),
        )
    )
