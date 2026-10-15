"""ORM -> DTO 序列化（集中一处，避免各 service 重复拼装）。"""
from __future__ import annotations

from app.db.models import FaceSample, Person, QrScanLog, RecognitionLog
from app.schemas.face import PersonBriefOut
from app.schemas.person import FaceSampleOut, PersonDetail, PersonOut, PersonUpdate
from app.schemas.recognition import QrScanLogOut, RecognitionLogDetail, RecognitionLogOut
from app.services.storage_service import get_storage


def face_out(face: FaceSample) -> FaceSampleOut:
    s = get_storage()
    return FaceSampleOut(
        id=face.id,
        person_id=face.person_id,
        vector_id=face.vector_id,
        engine=face.engine,
        model_name=face.model_name,
        dim=face.dim,
        is_primary=face.is_primary,
        image_url=s.to_url(face.image_path) or "",
        quality_score=round(float(face.quality_score), 4),
        face_width=face.face_width,
        face_height=face.face_height,
        det_score=round(float(face.det_score), 4),
        created_at=face.created_at,
    )


def person_out(person: Person, *, face_count: int | None = None, primary: FaceSample | None = None) -> PersonOut:
    s = get_storage()
    faces = list(person.faces or [])
    if primary is None and faces:
        primary = next((f for f in faces if f.is_primary), faces[0])
    return PersonOut(
        id=person.id,
        person_code=person.person_code,
        name=person.name,
        employee_no=person.employee_no,
        department=person.department,
        title=person.title,
        gender=person.gender,
        phone=person.phone,
        email=person.email,
        remark=person.remark,
        face_count=face_count if face_count is not None else len(faces),
        primary_image_url=s.to_url(primary.image_path) if primary else None,
        created_at=person.created_at,
        updated_at=person.updated_at,
    )


def person_brief(person: Person, *, face_count: int | None = None, primary: FaceSample | None = None) -> PersonBriefOut:
    s = get_storage()
    faces = list(person.faces or [])
    if primary is None and faces:
        primary = next((f for f in faces if f.is_primary), faces[0])
    return PersonBriefOut(
        id=person.id,
        person_code=person.person_code,
        name=person.name,
        employee_no=person.employee_no,
        department=person.department,
        title=person.title,
        gender=person.gender,
        phone=person.phone,
        email=person.email,
        remark=person.remark,
        face_count=face_count if face_count is not None else len(faces),
        primary_image_url=s.to_url(primary.image_path) if primary else None,
        created_at=person.created_at,
    )


def person_detail(
    person: Person,
    *,
    last_recognition_at=None,
    recognition_count: int = 0,
) -> PersonDetail:
    base = person_out(person)
    detail = PersonDetail(
        **base.model_dump(),
        faces=[face_out(f) for f in person.faces],
        last_recognition_at=last_recognition_at,
        recognition_count=recognition_count,
    )
    return detail


def recognition_out(log: RecognitionLog) -> RecognitionLogOut:
    s = get_storage()
    return RecognitionLogOut(
        id=log.id,
        person_id=log.person_id,
        person_name=log.person_name,
        person_code=log.person_code,
        matched_face_id=log.matched_face_id,
        similarity=round(float(log.similarity), 4),
        confidence=round(float(log.confidence), 4),
        is_matched=log.is_matched,
        threshold=round(float(log.threshold), 4),
        mode=log.mode,
        source=log.source,
        snapshot_url=s.to_url(log.snapshot_path),
        elapsed_ms=round(float(log.elapsed_ms), 2),
        created_at=log.created_at,
    )


def recognition_detail(log: RecognitionLog, *, top_k: list[dict] | None = None, person_image_url: str | None = None) -> RecognitionLogDetail:
    import json

    parsed: list[dict] = list(top_k or [])
    if not parsed and log.top_k_json:
        try:
            parsed = json.loads(log.top_k_json)
        except Exception:  # noqa: BLE001
            parsed = []
    base = recognition_out(log)
    return RecognitionLogDetail(
        **base.model_dump(),
        top_k=parsed,
        person_image_url=person_image_url,
    )


def qr_scan_out(row: QrScanLog) -> QrScanLogOut:
    return QrScanLogOut(
        id=row.id,
        person_id=row.person_id,
        person_name=row.person_name,
        is_valid=row.is_valid,
        client_ip=row.client_ip,
        created_at=row.created_at,
    )


__all__ = [
    "face_out",
    "person_brief",
    "person_detail",
    "person_out",
    "qr_scan_out",
    "recognition_detail",
    "recognition_out",
    "PersonUpdate",
]
