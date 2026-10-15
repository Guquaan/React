"""矢量库工厂：按配置选择实现，Chroma 不可用时自动降级到内置实现。"""
from __future__ import annotations

import logging
from functools import lru_cache

from app.core.config import get_settings
from app.repositories.vector.base import VectorHit, VectorRecord, VectorRepository

log = logging.getLogger(__name__)


def create_vector_repository(backend: str | None = None) -> VectorRepository:
    key = (backend or get_settings().vector_backend).lower()

    if key == "chroma":
        from app.repositories.vector.chroma_repo import ChromaVectorRepository

        repo = ChromaVectorRepository()
        if repo.is_ready():
            return repo
        log.warning("Chroma 不可用，自动降级到内置矢量库（数据目录 storage/vector_db）")

    from app.repositories.vector.local_repo import LocalVectorRepository

    return LocalVectorRepository()


@lru_cache(maxsize=1)
def get_vector_repository() -> VectorRepository:
    return create_vector_repository()


__all__ = [
    "VectorHit",
    "VectorRecord",
    "VectorRepository",
    "create_vector_repository",
    "get_vector_repository",
]
