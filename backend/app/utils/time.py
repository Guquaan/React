"""时间工具：统一使用带时区的 UTC 存储，前端负责转本地时间。"""
from __future__ import annotations

from datetime import datetime, timezone


def utcnow() -> datetime:
    """当前 UTC 时间（带时区信息）。"""
    return datetime.now(timezone.utc)


def to_iso(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat()


def from_epoch(seconds: float) -> datetime:
    return datetime.fromtimestamp(seconds, tz=timezone.utc)
