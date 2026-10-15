"""应用配置层。

所有可变参数集中在此处，其他层只允许通过 `get_settings()` 读取，
禁止在业务代码里散落硬编码常量 —— 这是"低耦合"的第一道保障。
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(BACKEND_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ---------------- 应用 ----------------
    app_name: str = "FaceID 人脸识别系统"
    app_env: Literal["dev", "prod"] = "dev"
    api_prefix: str = "/api/v1"
    host: str = "127.0.0.1"
    port: int = 8000
    cors_origins: str = (
        "http://localhost:5173,http://127.0.0.1:5173,"
        "http://localhost:115,http://127.0.0.1:115"
    )

    # ---------------- 存储 ----------------
    storage_dir: str = "storage"

    # ---------------- 矢量数据库 ----------------
    vector_backend: Literal["chroma", "local"] = "chroma"
    vector_collection: str = "face_embeddings"

    # ---------------- 人脸引擎 ----------------
    face_engine: Literal["arcface", "mock"] = "arcface"
    face_model_name: str = "arcface_r50"
    face_embedding_dim: int = 512
    face_det_score_threshold: float = 0.60
    face_min_size: int = 48

    # 模型文件名；留空则自动在 storage/models 下按候选顺序查找
    face_detector_filename: str = "face_detection_yunet_2023mar.onnx"
    face_recognizer_filename: str = ""

    # 注册质量闸门
    face_register_min_quality: float = 0.35

    # ---------------- 识别阈值 ----------------
    # 余弦相似度工作点：cosine >= threshold 判定为同一个人
    face_match_cosine_threshold: float = 0.40
    # 对外暴露的最低置信度（0~1）。默认 0.70 对应上面的余弦阈值
    face_confidence_floor: float = 0.70
    face_match_top_k: int = 5

    # ---------------- 安全（二维码签名） ----------------
    qr_secret_key: str = "change-me-in-production-faceid-demo"
    qr_token_ttl_seconds: int = 0  # 0 = 永不过期

    # ---------------- 前端地址（二维码扫码跳转用） ----------------
    frontend_base_url: str = "http://localhost:115"

    # ---------------- 文件上传 ----------------
    max_upload_mb: int = 8

    # ---------------------------------------------------------------
    @field_validator("face_min_size")
    @classmethod
    def _check_min_size(cls, v: int) -> int:
        if v < 16:
            raise ValueError("FACE_MIN_SIZE 不得小于 16")
        return v

    # ---------------- 派生路径 ----------------
    @property
    def storage_path(self) -> Path:
        p = Path(self.storage_dir)
        return p if p.is_absolute() else (BACKEND_DIR / p)

    @property
    def upload_dir(self) -> Path:
        return self.storage_path / "uploads"

    @property
    def snapshot_dir(self) -> Path:
        return self.storage_path / "snapshots"

    @property
    def model_dir(self) -> Path:
        return self.storage_path / "models"

    @property
    def vector_dir(self) -> Path:
        return self.storage_path / "vector_db"

    @property
    def sqlite_path(self) -> Path:
        return self.storage_path / "faceid.db"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    def ensure_dirs(self) -> None:
        for d in (
            self.storage_path,
            self.upload_dir,
            self.snapshot_dir,
            self.model_dir,
            self.vector_dir,
        ):
            d.mkdir(parents=True, exist_ok=True)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    s = Settings()
    s.ensure_dirs()
    return s
