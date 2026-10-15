"""仓储层：关系型元数据 + 矢量库。"""
from app.repositories.face_repo import FaceRepository
from app.repositories.log_repo import LogRepository
from app.repositories.person_repo import PersonRepository
from app.repositories.vector import (
    VectorHit,
    VectorRecord,
    VectorRepository,
    create_vector_repository,
    get_vector_repository,
)

__all__ = [
    "FaceRepository",
    "LogRepository",
    "PersonRepository",
    "VectorHit",
    "VectorRecord",
    "VectorRepository",
    "create_vector_repository",
    "get_vector_repository",
]
