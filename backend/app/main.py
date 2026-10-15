"""FastAPI 应用装配入口。

这里只做"组装"：中间件、异常处理、路由挂载、静态资源。
任何业务逻辑都不允许出现在本文件。
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api import api_router
from app.core.config import get_settings
from app.core.errors import AppError
from app.core.logging import setup_logging
from app.db import init_db
from app.engines import get_engine
from app.repositories.vector import get_vector_repository

log = logging.getLogger(__name__)

setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    s = get_settings()
    init_db()

    vectors = get_vector_repository()
    engine = get_engine()

    log.info("=" * 68)
    log.info(" %s 已启动", s.app_name)
    log.info(" 矢量库后端 : %s (%s)", vectors.backend_name, "就绪" if vectors.is_ready() else "不可用")
    log.info(" 人脸引擎   : %s (%s)", engine.name, "就绪" if engine.is_ready() else "未就绪")
    log.info(" 判定阈值   : cosine >= %.2f  置信度 >= %.0f%%", s.face_match_cosine_threshold, s.face_confidence_floor * 100)
    log.info(" 存储目录   : %s", s.storage_path)
    log.info(" 接口文档   : http://%s:%s/docs", s.host, s.port)
    log.info("=" * 68)

    if not engine.is_ready():
        log.warning(
            "人脸引擎未就绪！请执行：python scripts/download_models.py 下载模型；"
            "或在 backend/.env 中设置 FACE_ENGINE=mock 做离线联调。"
        )

    yield
    log.info("%s 已停止", s.app_name)


def create_app() -> FastAPI:
    s = get_settings()
    app = FastAPI(
        title=s.app_name,
        description=(
            "基于矢量数据库的人脸识别系统 —— 人脸注册、1:N 识别、识别时间追溯、二维码取数。\n\n"
            "**架构**：api → service → (repository, engine)，分层单向依赖。"
        ),
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=s.cors_origin_list or ["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Person-Code"],
    )

    # ---------------- 统一异常 -> JSON ----------------
    @app.exception_handler(AppError)
    async def _app_error_handler(_req: Request, exc: AppError):  # noqa: ANN202
        return JSONResponse(status_code=exc.http_status, content={"success": False, **exc.to_dict()})

    @app.exception_handler(Exception)
    async def _unhandled_handler(_req: Request, exc: Exception):  # noqa: ANN202
        log.exception("未处理异常: %s", exc)
        return JSONResponse(
            status_code=500,
            content={"success": False, "code": "INTERNAL_ERROR", "message": "服务器内部错误，请查看后端日志"},
        )

    # ---------------- 静态资源：上传的人脸图 / 抓拍快照 ----------------
    s.ensure_dirs()
    app.mount("/media", StaticFiles(directory=str(s.storage_path)), name="media")

    app.include_router(api_router, prefix=s.api_prefix)

    @app.get("/", include_in_schema=False)
    def root():
        return {
            "name": s.app_name,
            "docs": "/docs",
            "api_prefix": s.api_prefix,
            "media": "/media",
        }

    return app


app = create_app()
