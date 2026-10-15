"""人脸样本仓储。"""
from __future__ import annotations

from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.db.models import FaceSample


class FaceRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    # ---------------- 写 ----------------
    def create(self, **fields: Any) -> FaceSample:
        face = FaceSample(**fields)
        self.db.add(face)
        self.db.flush()
        return face

    def delete(self, face: FaceSample) -> None:
        self.db.delete(face)
        self.db.flush()

    def clear_primary(self, person_id: str) -> None:
        self.db.execute(
            update(FaceSample).where(FaceSample.person_id == person_id).values(is_primary=False)
        )
        self.db.flush()

    # ---------------- 读 ----------------
    def get(self, face_id: str) -> FaceSample | None:
        return self.db.get(FaceSample, face_id)

    def get_by_vector_id(self, vector_id: str) -> FaceSample | None:
        return self.db.scalar(select(FaceSample).where(FaceSample.vector_id == vector_id))

    def list_by_person(self, person_id: str) -> list[FaceSample]:
        return list(
            self.db.scalars(
                select(FaceSample)
                .where(FaceSample.person_id == person_id)
                .order_by(FaceSample.is_primary.desc(), FaceSample.created_at.desc())
            ).all()
        )

    def primary_of(self, person_id: str) -> FaceSample | None:
        return self.db.scalar(
            select(FaceSample)
            .where(FaceSample.person_id == person_id)
            .order_by(FaceSample.is_primary.desc(), FaceSample.created_at.asc())
            .limit(1)
        )

    def count(self) -> int:
        return int(self.db.scalar(select(func.count(FaceSample.id))) or 0)

    def count_by_person(self) -> dict[str, int]:
        rows = self.db.execute(
            select(FaceSample.person_id, func.count(FaceSample.id)).group_by(FaceSample.person_id)
        ).all()
        return {str(r[0]): int(r[1]) for r in rows}

    def all_vector_ids(self) -> list[str]:
        return list(self.db.scalars(select(FaceSample.vector_id)).all())
