"""二维码服务：生成带签名的二维码 + 扫码取数（含扫码审计日志）。

对应需求 4：「可以通过二维码获取相关人员的数据」。
设计要点：
  · 二维码里**不放明文身份信息**，只放 HMAC 签名 token，防篡改；
  · 扫码动作写入 `QrScanLog`，因此每一次取数都有时间和来源可追溯。
"""
from __future__ import annotations

import hashlib
import io
import logging
from datetime import timedelta

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import TokenInvalidError
from app.core.security import issue_token, parse_token
from app.db.models import Person
from app.repositories.face_repo import FaceRepository
from app.repositories.log_repo import LogRepository
from app.repositories.person_repo import PersonRepository
from app.schemas.recognition import QrPayloadOut, QrResolveOut
from app.services.serializers import (
    face_out,
    person_brief,
    recognition_out,
)
from app.services.storage_service import get_storage
from app.utils.time import utcnow

log = logging.getLogger(__name__)


class QrCodeService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.s = get_settings()
        self.storage = get_storage()
        self.persons = PersonRepository(db)
        self.faces = FaceRepository(db)
        self.logs = LogRepository(db)

    # ------------------------------------------------------------------
    def build_payload_by_id(self, person_id: str) -> QrPayloadOut:
        person = self.persons.get(person_id)
        if person is None:
            from app.core.errors import NotFoundError

            raise NotFoundError(f"人员不存在: {person_id}")
        return self.build_payload(person)

    def build_payload(self, person: Person) -> QrPayloadOut:
        token = issue_token(
            {"pid": person.id, "code": person.person_code, "n": person.name, "v": 1},
            self.s.qr_secret_key,
        )
        expires = (
            utcnow() + timedelta(seconds=self.s.qr_token_ttl_seconds)
            if self.s.qr_token_ttl_seconds > 0
            else None
        )
        base = self.s.frontend_base_url.rstrip("/")
        return QrPayloadOut(
            person_id=person.id,
            person_code=person.person_code,
            name=person.name,
            token=token,
            scan_url=f"{base}/#/scan?code={token}",
            resolve_url=f"{self.s.api_prefix}/qrcode/resolve?token={token}",
            expires_at=expires,
            generated_at=utcnow(),
        )

    def build_payload_by_id(self, person_id: str) -> QrPayloadOut:
        person = self.persons.get(person_id)
        if person is None:
            from app.core.errors import NotFoundError

            raise NotFoundError(f"人员不存在: {person_id}")
        return self.build_payload(person)

    def render_png(self, data: str, *, box_size: int = 10, border: int = 2) -> bytes:
        """把任意文本渲染成 PNG 二维码。"""
        import qrcode
        from qrcode.constants import ERROR_CORRECT_M

        qr = qrcode.QRCode(
            version=None,
            error_correction=ERROR_CORRECT_M,
            box_size=max(2, int(box_size)),
            border=max(0, int(border)),
        )
        qr.add_data(data)
        qr.make(fit=True)
        img = qr.make_image(fill_color="#111827", back_color="#FFFFFF").convert("RGB")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()

    def person_qrcode_png(self, person_id: str) -> tuple[bytes, QrPayloadOut]:
        person = self.persons.get(person_id)
        if person is None:
            from app.core.errors import NotFoundError

            raise NotFoundError(f"人员不存在: {person_id}")
        payload = self.build_payload(person)
        # 二维码内容用 resolve_url，普通手机扫码即可直接拿到数据
        return self.render_png(payload.resolve_url), payload

    # ------------------------------------------------------------------
    def resolve(
        self,
        token: str,
        *,
        client_ip: str | None = None,
        user_agent: str | None = None,
        recent_limit: int = 5,
    ) -> QrResolveOut:
        """校验 token 并返回该人员的完整数据（同时落一条扫码日志）。"""
        payload = parse_token(token, self.s.qr_secret_key, ttl_seconds=self.s.qr_token_ttl_seconds)
        if not payload:
            self.logs.add_qr_scan(
                person_id=None,
                person_name=None,
                token_digest=_digest(token),
                is_valid=False,
                client_ip=client_ip,
                user_agent=_trunc(user_agent),
            )
            self.db.commit()
            raise TokenInvalidError("二维码无效、已过期或被篡改")

        person = self.persons.get(str(payload.get("pid")))
        if person is None:
            self.logs.add_qr_scan(
                person_id=None,
                person_name=payload.get("n"),
                token_digest=_digest(token),
                is_valid=False,
                client_ip=client_ip,
                user_agent=_trunc(user_agent),
            )
            self.db.commit()
            raise TokenInvalidError("二维码对应的人员已不存在")

        self.logs.add_qr_scan(
            person_id=person.id,
            person_name=person.name,
            token_digest=_digest(token),
            is_valid=True,
            client_ip=client_ip,
            user_agent=_trunc(user_agent),
        )
        self.db.commit()

        faces = self.faces.list_by_person(person.id)
        recent_rows, _ = self.logs.list_recognitions(person_id=person.id, page=1, page_size=recent_limit)

        return QrResolveOut(
            valid=True,
            person=person_brief(person, face_count=len(faces)).model_dump(mode="json"),
            faces=[face_out(f).model_dump(mode="json") for f in faces],
            recent_recognitions=[recognition_out(r) for r in recent_rows],
            scanned_at=utcnow(),
            message=f"已获取 {person.name} 的档案数据",
        )

    # ------------------------------------------------------------------
    def list_scans(self, *, page: int = 1, page_size: int = 20):
        return self.logs.list_qr_scans(page=page, page_size=page_size)


def _digest(token: str) -> str:
    return hashlib.sha256((token or "").encode("utf-8")).hexdigest()[:32]


def _trunc(text: str | None, limit: int = 250) -> str | None:
    if not text:
        return None
    return text[:limit]
