"""业务服务层：编排仓储与引擎，承载全部业务规则。"""
from app.services.face_service import FaceService
from app.services.person_service import PersonService
from app.services.qrcode_service import QrCodeService
from app.services.recognition_service import RecognitionService
from app.services.scoring import (
    confidence_to_cosine,
    is_match,
    rank_candidates,
    should_accept_registration,
    to_confidence,
)
from app.services.stats_service import StatsService
from app.services.storage_service import StorageService, get_storage

__all__ = [
    "FaceService",
    "PersonService",
    "QrCodeService",
    "RecognitionService",
    "StatsService",
    "StorageService",
    "confidence_to_cosine",
    "get_storage",
    "is_match",
    "rank_candidates",
    "should_accept_registration",
    "to_confidence",
]
