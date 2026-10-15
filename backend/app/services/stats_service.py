"""统计服务：看板数据（含时间维度的趋势）。"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.repositories.face_repo import FaceRepository
from app.repositories.log_repo import LogRepository
from app.repositories.person_repo import PersonRepository
from app.repositories.vector import get_vector_repository
from app.schemas.recognition import DateCount, NameCount, StatsOverview


class StatsService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.s = get_settings()
        self.persons = PersonRepository(db)
        self.faces = FaceRepository(db)
        self.logs = LogRepository(db)
        self.vectors = get_vector_repository()

    def overview(self) -> StatsOverview:
        total = self.logs.recognition_total()
        matched = self.logs.recognition_matched()
        avg_conf, avg_ms = self.logs.avg_confidence_and_elapsed()

        return StatsOverview(
            person_count=self.persons.count(),
            face_count=self.faces.count(),
            recognition_total=total,
            recognition_matched=matched,
            recognition_today=self.logs.recognition_today(),
            match_rate=round(matched / total, 4) if total else 0.0,
            avg_confidence=round(avg_conf, 4),
            avg_elapsed_ms=round(avg_ms, 2),
            qr_scan_total=self.logs.qr_scan_total(),
            vector_backend=self.vectors.backend_name,
            face_engine=self.s.face_engine,
            cosine_threshold=float(self.s.face_match_cosine_threshold),
            confidence_floor=float(self.s.face_confidence_floor),
            department_distribution=[
                NameCount(name=n, count=c) for n, c in self.persons.department_distribution()
            ],
            trend_7d=[
                DateCount(date=d, total=t, matched=m) for d, t, m in self.logs.trend(days=7)
            ],
            top_recognized=[NameCount(name=n, count=c) for n, c in self.logs.top_recognized()],
        )
