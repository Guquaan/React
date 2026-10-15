"""Mock 人脸引擎 —— 供离线单元测试 / 无模型环境使用。

工作原理：以图像缩略图的像素统计量生成确定性伪特征。
  · 同一张图片 -> 完全相同的向量（相似度 1.0）
  · 不同图片   -> 向量近似正交（相似度 ≈ 0）

它不做真实的人脸检测，把整张图当作一张"脸"，因此可以用来验证：
仓储、服务、阈值判定、接口链路是否正确，而不需要下载 200MB 模型。
"""
from __future__ import annotations

import hashlib

import cv2
import numpy as np

from app.core.config import Settings, get_settings
from app.engines.base import DetectedFace, EmbeddingEngine
from app.utils.image import clamp_bbox


class MockEngine(EmbeddingEngine):
    name = "mock"
    model_name = "mock_engine"

    def __init__(self, settings: Settings | None = None) -> None:
        self.s = settings or get_settings()
        self.dim = self.s.face_embedding_dim

    def is_ready(self) -> bool:
        return True

    def detect(self, image: np.ndarray) -> list[DetectedFace]:
        h, w = image.shape[:2]
        bbox = clamp_bbox((int(w * 0.15), int(h * 0.15), int(w * 0.85), int(h * 0.85)), image.shape)
        return [DetectedFace(bbox=bbox, det_score=0.99, quality_score=0.9)]

    def embed_one(self, image: np.ndarray, face: DetectedFace) -> np.ndarray:
        x1, y1, x2, y2 = face.bbox
        crop = image[y1:y2, x1:x2]
        thumb = cv2.resize(crop, (16, 16), interpolation=cv2.INTER_AREA).astype(np.uint8)
        digest = hashlib.sha256(thumb.tobytes()).digest()

        rng = np.random.default_rng(int.from_bytes(digest[:8], "big"))
        vec = rng.standard_normal(self.dim).astype(np.float32)
        return self.normalize(vec)
