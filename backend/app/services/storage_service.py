"""文件存储服务：统一管理上传图片 / 抓拍快照的落盘与 URL 映射。

业务层只拿"相对路径"，由本模块决定物理位置；
以后要换成 OSS/S3，只改这一个文件。
"""
from __future__ import annotations

from pathlib import Path

import numpy as np

from app.core.config import get_settings
from app.utils.ids import new_id, safe_filename
from app.utils.image import write_image

MEDIA_URL_PREFIX = "/media"


class StorageService:
    def __init__(self) -> None:
        self.s = get_settings()

    # ---------------- 路径换算 ----------------
    def abs_path(self, rel_path: str) -> Path:
        return self.s.storage_path / rel_path

    def to_url(self, rel_path: str | None) -> str | None:
        if not rel_path:
            return None
        return f"{MEDIA_URL_PREFIX}/{rel_path.replace('\\\\', '/').lstrip('/')}"

    # ---------------- 写入 ----------------
    def save_bytes(self, data: bytes, *, subdir: str, filename: str) -> str:
        rel = f"uploads/{subdir}/{safe_filename(filename)}"
        path = self.abs_path(rel)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return rel

    def save_image(
        self,
        img: np.ndarray,
        *,
        subdir: str,
        prefix: str = "img",
        suffix: str = ".jpg",
        quality: int = 92,
    ) -> str:
        rel = f"uploads/{subdir}/{prefix}_{new_id()}{suffix}"
        write_image(self.abs_path(rel), img, quality=quality)
        return rel

    def save_snapshot(self, img: np.ndarray, *, prefix: str = "cap") -> str:
        rel = f"snapshots/{prefix}_{new_id()}.jpg"
        write_image(self.abs_path(rel), img, quality=88)
        return rel

    # ---------------- 删除（幂等） ----------------
    def remove(self, rel_path: str | None) -> None:
        if not rel_path:
            return
        try:
            self.abs_path(rel_path).unlink(missing_ok=True)
        except OSError:
            pass


_storage: StorageService | None = None


def get_storage() -> StorageService:
    global _storage
    if _storage is None:
        _storage = StorageService()
    return _storage
