"""系统路由：健康检查 / 统计看板 / 配置只读。"""
from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import settings_dep, stats_service
from app.core.config import Settings
from app.engines import get_engine
from app.repositories.vector import get_vector_repository
from app.schemas.common import ApiResponse, HealthOut
from app.services import StatsService

router = APIRouter(tags=["系统"])


@router.get("/health", response_model=ApiResponse[HealthOut], summary="健康检查（模型与矢量库状态）")
def health(s: Settings = Depends(settings_dep), svc: StatsService = Depends(stats_service)):
    engine = get_engine()
    vectors = get_vector_repository()
    overview = svc.overview()
    return ApiResponse(
        data=HealthOut(
            status="ok",
            app_name=s.app_name,
            env=s.app_env,
            vector_backend=vectors.backend_name,
            vector_backend_ready=vectors.is_ready(),
            face_engine=engine.name,
            engine_ready=engine.is_ready(),
            cosine_threshold=s.face_match_cosine_threshold,
            confidence_floor=s.face_confidence_floor,
            person_count=overview.person_count,
            face_count=overview.face_count,
            log_count=overview.recognition_total,
        )
    )


@router.get("/stats/overview", response_model=ApiResponse, summary="看板统计（趋势 / 分布 / 平均置信度）")
def stats_overview(svc: StatsService = Depends(stats_service)):
    return ApiResponse(data=svc.overview())


@router.get("/config", response_model=ApiResponse[dict], summary="只读配置（前端展示阈值用）")
def read_config(s: Settings = Depends(settings_dep)):
    return ApiResponse(
        data={
            "app_name": s.app_name,
            "env": s.app_env,
            "api_prefix": s.api_prefix,
            "vector_backend": s.vector_backend,
            "vector_collection": s.vector_collection,
            "face_engine": s.face_engine,
            "face_model_name": s.face_model_name,
            "face_embedding_dim": s.face_embedding_dim,
            "face_match_cosine_threshold": s.face_match_cosine_threshold,
            "face_confidence_floor": s.face_confidence_floor,
            "face_match_top_k": s.face_match_top_k,
            "face_min_size": s.face_min_size,
        }
    )
