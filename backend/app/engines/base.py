"""人脸引擎抽象层。

这是"低耦合"的关键：业务层（services）只依赖 `EmbeddingEngine` 抽象，
换算法（ArcFace / FaceNet / 云端 API / Mock）只需新增一个实现类并改一行配置。
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

import numpy as np


@dataclass(slots=True)
class DetectedFace:
    """检测框结果。bbox 为 (x1, y1, x2, y2) 像素坐标。"""

    bbox: tuple[int, int, int, int]
    det_score: float
    landmarks: np.ndarray | None = None  # (5, 2) 左眼/右眼/鼻尖/左嘴角/右嘴角
    quality_score: float = 0.0

    @property
    def width(self) -> int:
        return self.bbox[2] - self.bbox[0]

    @property
    def height(self) -> int:
        return self.bbox[3] - self.bbox[1]

    @property
    def area(self) -> int:
        return max(0, self.width) * max(0, self.height)


@dataclass(slots=True)
class FaceEmbedding:
    """一张人脸的最终特征。"""

    embedding: np.ndarray                 # (dim,) float32，已 L2 归一化
    bbox: tuple[int, int, int, int]
    det_score: float
    quality_score: float
    landmarks: np.ndarray | None = None
    extra: dict = field(default_factory=dict)


class EmbeddingEngine(ABC):
    """人脸特征提取引擎接口。"""

    name: str = "base"
    model_name: str = "base"
    dim: int = 512

    # ---------------- 生命周期 ----------------
    def load(self) -> None:  # pragma: no cover - 可选实现
        """加载模型（幂等）。默认不做任何事。"""

    def is_ready(self) -> bool:
        """模型是否可用。不可用时 API 返回明确提示，而不是崩溃。"""
        return True

    @property
    def ready(self) -> bool:
        return self.is_ready()

    # ---------------- 能力 ----------------
    @abstractmethod
    def detect(self, image: np.ndarray) -> list[DetectedFace]:
        """检测图中所有人脸。"""

    @abstractmethod
    def embed_one(self, image: np.ndarray, face: DetectedFace) -> np.ndarray:
        """把单张人脸转成归一化特征向量。"""

    # ---------------- 组合能力（默认实现，子类可覆盖优化） ----------------
    def detect_and_embed(self, image: np.ndarray) -> list[FaceEmbedding]:
        out: list[FaceEmbedding] = []
        for face in self.detect(image):
            vec = self.embed_one(image, face)
            out.append(
                FaceEmbedding(
                    embedding=vec,
                    bbox=face.bbox,
                    det_score=face.det_score,
                    quality_score=face.quality_score,
                    landmarks=face.landmarks,
                )
            )
        return out

    # ---------------- 静态工具 ----------------
    @staticmethod
    def normalize(vec: np.ndarray) -> np.ndarray:
        v = np.asarray(vec, dtype=np.float32).reshape(-1)
        norm = float(np.linalg.norm(v))
        if norm < 1e-12:
            return v
        return (v / norm).astype(np.float32)

    @staticmethod
    def cosine(a: np.ndarray, b: np.ndarray) -> float:
        """两个已归一化向量的余弦相似度。"""
        return float(np.clip(np.dot(a, b), -1.0, 1.0))
