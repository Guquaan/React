"""识别记录 / 扫码记录仓储。"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import Integer, func, select
from sqlalchemy.orm import Session

from app.db.models import QrScanLog, RecognitionLog
from app.utils.time import utcnow


class LogRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    # ---------------- 写 ----------------
    def add_recognition(self, **fields: Any) -> RecognitionLog:
        row = RecognitionLog(**fields)
        self.db.add(row)
        self.db.flush()
        return row

    def add_qr_scan(self, **fields: Any) -> QrScanLog:
        row = QrScanLog(**fields)
        self.db.add(row)
        self.db.flush()
        return row

    # ---------------- 识别记录查询 ----------------
    def list_recognitions(
        self,
        *,
        page: int = 1,
        page_size: int = 20,
        person_id: str | None = None,
        is_matched: bool | None = None,
        mode: str | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> tuple[list[RecognitionLog], int]:
        stmt = select(RecognitionLog)
        count_stmt = select(func.count(RecognitionLog.id))

        conds = []
        if person_id:
            conds.append(RecognitionLog.person_id == person_id)
        if is_matched is not None:
            conds.append(RecognitionLog.is_matched.is_(is_matched))
        if mode:
            conds.append(RecognitionLog.mode == mode)
        if start:
            conds.append(RecognitionLog.created_at >= start)
        if end:
            conds.append(RecognitionLog.created_at <= end)
        for c in conds:
            stmt = stmt.where(c)
            count_stmt = count_stmt.where(c)

        total = int(self.db.scalar(count_stmt) or 0)
        stmt = stmt.order_by(RecognitionLog.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        return list(self.db.scalars(stmt).all()), total

    def last_recognition_of(self, person_id: str) -> RecognitionLog | None:
        return self.db.scalar(
            select(RecognitionLog)
            .where(RecognitionLog.person_id == person_id)
            .order_by(RecognitionLog.created_at.desc())
            .limit(1)
        )

    def count_recognitions_of(self, person_id: str) -> int:
        return int(
            self.db.scalar(
                select(func.count(RecognitionLog.id)).where(RecognitionLog.person_id == person_id)
            )
            or 0
        )

    # ---------------- 统计 ----------------
    def recognition_total(self) -> int:
        return int(self.db.scalar(select(func.count(RecognitionLog.id))) or 0)

    def recognition_matched(self) -> int:
        return int(
            self.db.scalar(
                select(func.count(RecognitionLog.id)).where(RecognitionLog.is_matched.is_(True))
            )
            or 0
        )

    def recognition_today(self) -> int:
        start = utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        return int(
            self.db.scalar(
                select(func.count(RecognitionLog.id)).where(RecognitionLog.created_at >= start)
            )
            or 0
        )

    def avg_confidence_and_elapsed(self) -> tuple[float, float]:
        row = self.db.execute(
            select(
                func.coalesce(func.avg(RecognitionLog.confidence), 0.0),
                func.coalesce(func.avg(RecognitionLog.elapsed_ms), 0.0),
            ).where(RecognitionLog.is_matched.is_(True))
        ).one()
        return float(row[0]), float(row[1])

    def trend(self, days: int = 7) -> list[tuple[str, int, int]]:
        start = (utcnow() - timedelta(days=days - 1)).replace(hour=0, minute=0, second=0, microsecond=0)
        rows = self.db.execute(
            select(
                func.strftime("%Y-%m-%d", RecognitionLog.created_at),
                func.count(RecognitionLog.id),
                func.sum(func.cast(RecognitionLog.is_matched, Integer)),
            )
            .where(RecognitionLog.created_at >= start)
            .group_by(func.strftime("%Y-%m-%d", RecognitionLog.created_at))
        ).all()
        found = {str(r[0]): (int(r[1]), int(r[2] or 0)) for r in rows}

        out: list[tuple[str, int, int]] = []
        for i in range(days - 1, -1, -1):
            day = (utcnow() - timedelta(days=i)).strftime("%Y-%m-%d")
            total, matched = found.get(day, (0, 0))
            out.append((day, total, matched))
        return out

    def top_recognized(self, limit: int = 5) -> list[tuple[str, int]]:
        rows = self.db.execute(
            select(RecognitionLog.person_name, func.count(RecognitionLog.id))
            .where(RecognitionLog.is_matched.is_(True), RecognitionLog.person_name.is_not(None))
            .group_by(RecognitionLog.person_name)
            .order_by(func.count(RecognitionLog.id).desc())
            .limit(limit)
        ).all()
        return [(str(r[0]), int(r[1])) for r in rows]

    # ---------------- 扫码记录 ----------------
    def qr_scan_total(self) -> int:
        return int(self.db.scalar(select(func.count(QrScanLog.id))) or 0)

    def list_qr_scans(self, *, page: int = 1, page_size: int = 20) -> tuple[list[QrScanLog], int]:
        total = self.qr_scan_total()
        stmt = (
            select(QrScanLog)
            .order_by(QrScanLog.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list(self.db.scalars(stmt).all()), total
