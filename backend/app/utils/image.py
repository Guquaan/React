"""图像工具（纯函数，无副作用，便于单测）。"""
from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np


def decode_image(data: bytes) -> np.ndarray:
    """字节流 -> BGR ndarray。失败抛 ValueError。"""
    arr = np.frombuffer(data, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("无法解码图片，请确认是有效的 JPG/PNG 文件")
    return img


def read_image(path: str | Path) -> np.ndarray:
    img = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError(f"无法读取图片: {path}")
    return img


def encode_jpeg(img: np.ndarray, quality: int = 92) -> bytes:
    ok, buf = cv2.imencode(".jpg", img, [int(cv2.IMWRITE_JPEG_QUALITY), quality])
    if not ok:
        raise ValueError("图片编码失败")
    return buf.tobytes()


def write_image(path: str | Path, img: np.ndarray, quality: int = 92) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    suffix = p.suffix.lower() or ".jpg"
    if suffix in (".jpg", ".jpeg"):
        ok, buf = cv2.imencode(suffix, img, [int(cv2.IMWRITE_JPEG_QUALITY), quality])
    else:
        ok, buf = cv2.imencode(suffix, img)
    if not ok:
        raise ValueError(f"图片写入失败: {p}")
    p.write_bytes(buf.tobytes())


def resize_max(img: np.ndarray, max_side: int = 1280) -> np.ndarray:
    """长边超过 max_side 时等比缩放，保证推理耗时可控。"""
    h, w = img.shape[:2]
    longest = max(h, w)
    if longest <= max_side:
        return img
    scale = max_side / float(longest)
    return cv2.resize(img, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)


def crop_with_margin(
    img: np.ndarray, bbox: tuple[int, int, int, int], margin: float = 0.18
) -> np.ndarray:
    """按人脸框裁剪，四周留出 margin 比例的边距（更接近人眼观感）。"""
    x1, y1, x2, y2 = bbox
    w, h = x2 - x1, y2 - y1
    mx, my = int(w * margin), int(h * margin)
    ih, iw = img.shape[:2]
    nx1, ny1 = max(0, x1 - mx), max(0, y1 - my)
    nx2, ny2 = min(iw, x2 + mx), min(ih, y2 + my)
    if nx2 <= nx1 or ny2 <= ny1:
        return img
    return img[ny1:ny2, nx1:nx2].copy()


def clamp_bbox(bbox: tuple[int, int, int, int], shape: tuple[int, ...]) -> tuple[int, int, int, int]:
    h, w = shape[:2]
    x1, y1, x2, y2 = bbox
    x1 = max(0, min(int(x1), w - 1))
    y1 = max(0, min(int(y1), h - 1))
    x2 = max(x1 + 1, min(int(x2), w))
    y2 = max(y1 + 1, min(int(y2), h))
    return x1, y1, x2, y2


def blur_score(gray: np.ndarray) -> float:
    """Laplacian 方差，越大越清晰。用于质量筛选。"""
    return float(cv2.Laplacian(gray, cv2.CV_64F).var())
