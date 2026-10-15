"""数据库连接与会话（仅关系型元数据；向量走矢量库）。"""
from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_settings


class Base(DeclarativeBase):
    """所有 ORM 模型的基类。"""


_settings = get_settings()
_engine = create_engine(
    f"sqlite:///{_settings.sqlite_path.as_posix()}",
    echo=False,
    future=True,
    connect_args={"check_same_thread": False},
)


@event.listens_for(_engine, "connect")
def _set_sqlite_pragma(dbapi_conn, _record):  # noqa: ANN001
    """开启外键约束 + WAL，兼顾完整性与并发读。"""
    cur = dbapi_conn.cursor()
    cur.execute("PRAGMA foreign_keys=ON")
    cur.execute("PRAGMA journal_mode=WAL")
    cur.close()


SessionLocal = sessionmaker(bind=_engine, autoflush=False, expire_on_commit=False, class_=Session)


def get_engine():  # noqa: ANN201
    return _engine


def init_db() -> None:
    """建表（幂等）。"""
    from app.db import models  # noqa: F401  确保模型已注册到 metadata

    Base.metadata.create_all(bind=_engine)


@contextmanager
def session_scope() -> Iterator[Session]:
    """上下文管理器式会话：正常提交、异常回滚、最终关闭。"""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def get_db() -> Iterator[Session]:
    """FastAPI 依赖注入用。"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
