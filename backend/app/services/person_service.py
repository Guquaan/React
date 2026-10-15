"""人员服务：档案 CRUD + 与矢量库/文件的级联清理。"""
from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.core.errors import ConflictError, NotFoundError
from app.db.models import Person
from app.repositories.face_repo import FaceRepository
from app.repositories.log_repo import LogRepository
from app.repositories.person_repo import PersonRepository
from app.repositories.vector import VectorRepository, get_vector_repository
from app.schemas.common import PageMeta
from app.schemas.person import PersonCreate, PersonDetail, PersonOut, PersonUpdate
from app.services.serializers import person_detail, person_out
from app.services.storage_service import StorageService, get_storage

log = logging.getLogger(__name__)


class PersonService:
    def __init__(
        self,
        db: Session,
        *,
        vectors: VectorRepository | None = None,
        storage: StorageService | None = None,
    ) -> None:
        self.db = db
        self.vectors = vectors or get_vector_repository()
        self.storage = storage or get_storage()
        self.persons = PersonRepository(db)
        self.faces = FaceRepository(db)
        self.logs = LogRepository(db)

    # ------------------------------------------------------------------
    def create(self, payload: PersonCreate) -> PersonOut:
        if payload.employee_no and self.persons.get_by_employee_no(payload.employee_no):
            raise ConflictError(f"工号/学号已存在: {payload.employee_no}")

        person = self.persons.create(**payload.model_dump())
        self.db.commit()
        log.info("创建人员 id=%s code=%s name=%s", person.id, person.person_code, person.name)
        return person_out(person, face_count=0)

    def update(self, person_id: str, payload: PersonUpdate) -> PersonOut:
        person = self._must_get(person_id)
        fields = payload.model_dump(exclude_unset=True)

        new_no = fields.get("employee_no")
        if new_no and new_no != person.employee_no:
            exists = self.persons.get_by_employee_no(new_no)
            if exists and exists.id != person.id:
                raise ConflictError(f"工号/学号已存在: {new_no}")

        self.persons.update(person, **fields)
        self.db.commit()
        return person_out(person)

    def delete(self, person_id: str) -> dict[str, int]:
        """删除人员：DB 级联删除人脸记录，同时清理矢量库与磁盘文件。"""
        person = self._must_get(person_id)
        faces = self.faces.list_by_person(person_id)
        vector_ids = [f.vector_id for f in faces]
        paths = [f.image_path for f in faces]

        self.persons.delete(person)
        self.db.commit()

        removed_vectors = self.vectors.delete(vector_ids) if vector_ids else 0
        for p in paths:
            self.storage.remove(p)

        log.info("删除人员 id=%s 人脸样本=%d 向量=%d", person_id, len(faces), removed_vectors)
        return {"faces_deleted": len(faces), "vectors_deleted": removed_vectors}

    # ------------------------------------------------------------------
    def get(self, person_id: str) -> PersonDetail:
        person = self._must_get(person_id)
        last = self.logs.last_recognition_of(person_id)
        return person_detail(
            person,
            last_recognition_at=last.created_at if last else None,
            recognition_count=self.logs.count_recognitions_of(person_id),
        )

    def get_by_code(self, person_code: str) -> PersonDetail:
        person = self.persons.get_by_code(person_code)
        if person is None:
            raise NotFoundError(f"人员编号不存在: {person_code}")
        return self.get(person.id)

    def list(
        self,
        *,
        page: int = 1,
        page_size: int = 20,
        keyword: str | None = None,
        department: str | None = None,
    ) -> tuple[list[PersonOut], PageMeta]:
        page = max(1, page)
        page_size = min(max(1, page_size), 200)
        rows, total = self.persons.list(
            page=page, page_size=page_size, keyword=keyword, department=department
        )
        counts = self.faces.count_by_person()
        items = [
            person_out(
                p,
                face_count=counts.get(p.id, 0),
                primary=self.faces.primary_of(p.id),
            )
            for p in rows
        ]
        pages = (total + page_size - 1) // page_size
        return items, PageMeta(total=total, page=page, page_size=page_size, pages=pages)

    def departments(self) -> list[str]:
        return self.persons.distinct_departments()

    # ------------------------------------------------------------------
    def _must_get(self, person_id: str) -> Person:
        person = self.persons.get(person_id)
        if person is None:
            raise NotFoundError(f"人员不存在: {person_id}")
        return person
