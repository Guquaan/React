"""ArcFace(ONNX) 人脸引擎实现。

Detector : YuNet  (OpenCV 内置 FaceDetectorYN，输出 5 点关键点)
Recognizer: ArcFace ResNet50 (InsightFace w600k_r50)，输出 512 维特征

两者都是 ONNX，用 onnxruntime 推理，不需要 Visual Studio / CMake 编译，
Windows 上 `pip install` 即可跑通。
"""
from __future__ import annotations

import logging
from pathlib import Path

import cv2
import numpy as np

from app.core.config import Settings, get_settings
from app.engines.base import DetectedFace, EmbeddingEngine
from app.utils.image import blur_score, clamp_bbox

log = logging.getLogger(__name__)

# ArcFace 标准对齐模板（112x112 下的 5 点坐标）
_ARCFACE_DST = np.array(
    [
        [38.2946, 51.6963],
        [73.5318, 51.5014],
        [56.0252, 71.7366],
        [41.5493, 92.3655],
        [70.7299, 92.2041],
    ],
    dtype=np.float32,
)

_DETECTOR_FILE = "face_detection_yunet_2023mar.onnx"
# 按优先级自动探测已下载的识别模型
_RECOGNIZER_CANDIDATES = ("w600k_r50.onnx", "w600k_mbf.onnx")
_RECOGNIZER_MODEL_NAMES = {
    "w600k_r50.onnx": "arcface_r50",
    "w600k_mbf.onnx": "arcface_mbf",
}


class ArcFaceOnnxEngine(EmbeddingEngine):
    name = "arcface"
    model_name = "arcface_r50"

    def __init__(self, settings: Settings | None = None) -> None:
        self.s = settings or get_settings()
        self.dim = self.s.face_embedding_dim
        self._detector = None
        self._session = None
        self._input_name = "input.1"
        self._load_error: str | None = None
        self._recognizer_file: Path | None = self._resolve_recognizer()
        self.model_name = (
            _RECOGNIZER_MODEL_NAMES.get(self._recognizer_file.name, self.s.face_model_name)
            if self._recognizer_file
            else self.s.face_model_name
        )
        self._load()

    # ------------------------------------------------------------------
    # 加载
    # ------------------------------------------------------------------
    @property
    def detector_path(self) -> Path:
        return self.s.model_dir / (self.s.face_detector_filename or _DETECTOR_FILE)

    def _resolve_recognizer(self) -> Path | None:
        if self.s.face_recognizer_filename:
            explicit = self.s.model_dir / self.s.face_recognizer_filename
            return explicit if explicit.exists() else None
        for name in _RECOGNIZER_CANDIDATES:
            candidate = self.s.model_dir / name
            if candidate.exists():
                return candidate
        return None

    @property
    def recognizer_path(self) -> Path:
        return self._recognizer_file or (self.s.model_dir / _RECOGNIZER_CANDIDATES[0])

    def _load(self) -> None:
        try:
            self._load_detector()
            self._load_recognizer()
        except Exception as exc:  # noqa: BLE001
            self._load_error = f"{type(exc).__name__}: {exc}"
            log.warning("ArcFace 引擎加载失败: %s", self._load_error)

    def _load_detector(self) -> None:
        if not hasattr(cv2, "FaceDetectorYN"):
            raise RuntimeError(
                "当前 opencv 版本不支持 FaceDetectorYN，请升级 opencv-python>=4.7"
            )
        if not self.detector_path.exists():
            raise FileNotFoundError(f"缺少检测模型: {self.detector_path}")
        self._detector = cv2.FaceDetectorYN.create(
            model=str(self.detector_path),
            config="",
            input_size=(320, 320),
            score_threshold=float(self.s.face_det_score_threshold),
            nms_threshold=0.3,
            top_k=50,
        )

    def _load_recognizer(self) -> None:
        if not self.recognizer_path.exists():
            raise FileNotFoundError(f"缺少识别模型: {self.recognizer_path}")
        import onnxruntime as ort

        opts = ort.SessionOptions()
        opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        opts.intra_op_num_threads = 0  # 0 = 自动
        self._session = ort.InferenceSession(
            str(self.recognizer_path), sess_options=opts, providers=["CPUExecutionProvider"]
        )
        self._input_name = self._session.get_inputs()[0].name

    def is_ready(self) -> bool:
        return self._detector is not None and self._session is not None

    @property
    def load_error(self) -> str | None:
        return self._load_error

    # ------------------------------------------------------------------
    # 检测
    # ------------------------------------------------------------------
    def detect(self, image: np.ndarray) -> list[DetectedFace]:
        if self._detector is None:
            raise RuntimeError(
                "人脸检测模型未就绪，请先执行 `python scripts/download_models.py`。"
                f"{(' 详情: ' + self._load_error) if self._load_error else ''}"
            )

        h, w = image.shape[:2]
        # YuNet 需要显式告知输入尺寸
        self._detector.setInputSize((w, h))
        _, raw = self._detector.detect(image)
        if raw is None or len(raw) == 0:
            return []

        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        faces: list[DetectedFace] = []
        for row in raw:
            x, y, bw, bh = (float(row[0]), float(row[1]), float(row[2]), float(row[3]))
            det_score = float(row[-1])
            if bw < self.s.face_min_size or bh < self.s.face_min_size:
                continue

            bbox = clamp_bbox((int(x), int(y), int(x + bw), int(y + bh)), image.shape)
            landmarks = np.array(
                [
                    [row[4], row[5]],
                    [row[6], row[7]],
                    [row[8], row[9]],
                    [row[10], row[11]],
                    [row[12], row[13]],
                ],
                dtype=np.float32,
            )
            faces.append(
                DetectedFace(
                    bbox=bbox,
                    det_score=det_score,
                    landmarks=landmarks,
                    quality_score=self._quality(gray, bbox, det_score),
                )
            )
        faces.sort(key=lambda f: f.area, reverse=True)
        return faces

    @staticmethod
    def _quality(gray: np.ndarray, bbox: tuple[int, int, int, int], det_score: float) -> float:
        """0~1 的质量分 = 0.6*检测置信度 + 0.4*清晰度归一化。"""
        x1, y1, x2, y2 = bbox
        patch = gray[y1:y2, x1:x2]
        sharp = blur_score(patch) if patch.size else 0.0
        sharp_norm = float(min(1.0, sharp / 500.0))
        size_bonus = float(min(1.0, min(patch.shape[:2] if patch.size else (0, 0)) / 160.0))
        return float(np.clip(0.5 * det_score + 0.3 * sharp_norm + 0.2 * size_bonus, 0.0, 1.0))

    # ------------------------------------------------------------------
    # 对齐 + 特征
    # ------------------------------------------------------------------
    def _align(self, image: np.ndarray, face: DetectedFace) -> np.ndarray:
        if face.landmarks is not None and len(face.landmarks) == 5:
            mat, _ = cv2.estimateAffinePartial2D(face.landmarks, _ARCFACE_DST, method=cv2.LMEDS)
            if mat is not None:
                return cv2.warpAffine(image, mat, (112, 112), borderValue=0.0)
        # 退化路径：直接裁剪缩放（无关键点时准确率会下降，但不会崩）
        x1, y1, x2, y2 = face.bbox
        crop = image[y1:y2, x1:x2]
        return cv2.resize(crop, (112, 112), interpolation=cv2.INTER_LINEAR)

    def embed_one(self, image: np.ndarray, face: DetectedFace) -> np.ndarray:
        if self._session is None:
            raise RuntimeError("人脸识别模型未就绪，请先执行 `python scripts/download_models.py`")

        aligned = self._align(image, face)
        rgb = cv2.cvtColor(aligned, cv2.COLOR_BGR2RGB).astype(np.float32)
        rgb = (rgb - 127.5) / 127.5
        blob = np.transpose(rgb, (2, 0, 1))[None, ...]  # NCHW

        outputs = self._session.run(None, {self._input_name: blob})
        vec = np.asarray(outputs[0], dtype=np.float32).reshape(-1)
        return self.normalize(vec)
