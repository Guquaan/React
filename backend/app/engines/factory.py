"""引擎工厂 —— 唯一的"选择实现"的地方。

新增算法只需：写一个 EmbeddingEngine 子类 + 在 _REGISTRY 注册 + 改配置。
services 层代码零改动。
"""
from __future__ import annotations

from functools import lru_cache

from app.core.config import get_settings
from app.engines.base import DetectedFace, EmbeddingEngine, FaceEmbedding
from app.engines.mock import MockEngine

_REGISTRY: dict[str, type[EmbeddingEngine]] = {
    "mock": MockEngine,
}


def _register_lazy(name: str, factory) -> None:  # noqa: ANN001
    _REGISTRY[name] = factory


def _arcface_factory(*args, **kwargs) -> EmbeddingEngine:
    from app.engines.arcface_onnx import ArcFaceOnnxEngine

    return ArcFaceOnnxEngine(*args, **kwargs)


_register_lazy("arcface", _arcface_factory)


def create_engine(name: str | None = None) -> EmbeddingEngine:
    key = (name or get_settings().face_engine).lower()
    factory = _REGISTRY.get(key)
    if factory is None:
        raise ValueError(f"未知的人脸引擎: {key}，可选: {sorted(_REGISTRY)}")
    return factory()


@lru_cache(maxsize=1)
def get_engine() -> EmbeddingEngine:
    """全局单例引擎（模型加载开销大，必须复用）。"""
    return create_engine()


__all__ = [
    "DetectedFace",
    "EmbeddingEngine",
    "FaceEmbedding",
    "create_engine",
    "get_engine",
]
