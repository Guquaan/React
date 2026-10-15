"""人员仓储 —— 只做数据存取，不含业务规则。"""
from __future__ import annotations

from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.db.models import Person


class PersonRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    # ---------------- 写 ----------------
    def create(self, **fields: Any) -> Person:
        person = Person(**fields)
        self.db.add(person)
        self.db.flush()
        return person

    def update(self, person: Person, **fields: Any) -> Person:
        for k, v in fields.items():
            if v is not None:
                setattr(person, k, v)
        self.db.flush()
        return person

    def delete(self, person: Person) -> None:
        self.db.delete(person)
        self.db.flush()

    # ---------------- 读 ----------------
    def get(self, person_id: str) -> Person | None:
        return self.db.get(Person, person_id)

    def get_by_code(self, person_code: str) -> Person | None:
        return self.db.scalar(select(Person).where(Person.person_code == person_code))

    def get_by_employee_no(self, employee_no: str) -> Person | None:
        return self.db.scalar(select(Person).where(Person.employee_no == employee_no))

    def list(
        self,
        *,
        page: int = 1,
        page_size: int = 20,
        keyword: str | None = None,
        department: str | None = None,
        has_face: bool | None = None,
    ) -> tuple[list[Person], int]:
        stmt = select(Person)
        count_stmt = select(func.count(Person.id))

        conditions = []
        if keyword:
            like = f"%{keyword.strip()}%"
            conditions.append(
                or_(
                    Person.name.like(like),
                    Person.person_code.like(like),
                    Person.employee_no.like(like),
                    Person.department.like(like),
                )
            )
        if department:
            conditions.append(Person.department == department)
        for c in conditions:
            stmt = stmt.where(c)
            count_stmt = count_stmt.where(c)

        total = int(self.db.scalar(count_stmt) or 0)
        stmt = stmt.order_by(Person.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        return list(self.db.scalars(stmt).all()), total

    def all_ids(self) -> list[str]:
        return list(self.db.scalars(select(Person.id)).all())

    def count(self) -> int:
        return int(self.db.scalar(select(func.count(Person.id))) or 0)

    def department_distribution(self, limit: int = 10) -> list[tuple[str, int]]:
        rows = self.db.execute(
            select(func.coalesce(Person.department, "未填写").label("dep"), func.count(Person.id))
            .group_by("dep")
            .order_by(func.count(Person.id).desc())
            .limit(limit)
        ).all()
        return [(str(r[0]), int(r[1])) for r in rows]

    def distinct_departments(self) -> list[str]:
        rows = self.db.scalars(
            select(Person.department).where(Person.department.is_not(None)).distinct()
        ).all()
        return sorted({str(r) for r in rows if r})
