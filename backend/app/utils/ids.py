"""ID / 文件名工具。"""
from __future__ import annotations

import re
import uuid
from pathlib import Path

_SAFE = re.compile(r"[^A-Za-z0-9_.-]")
_ALLOWED_IMAGE_SUFFIX = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


def new_id(prefix: str = "") -> str:
    raw = uuid.uuid4().hex
    return f"{prefix}{raw}" if prefix else raw


def new_person_code() -> str:
    """对外展示的人员编号，如 P-3F9A2C1D。"""
    return "P-" + uuid.uuid4().hex[:8].upper()


def safe_filename(name: str, *, fallback_suffix: str = ".jpg") -> str:
    """把用户上传的文件名清洗成安全的存储名。"""
    stem = Path(name or "").stem
    suffix = Path(name or "").suffix.lower()
    if suffix not in _ALLOWED_IMAGE_SUFFIX:
        suffix = fallback_suffix
    stem = _SAFE.sub("_", stem)[:40] or "image"
    return f"{stem}_{uuid.uuid4().hex[:8]}{suffix}"


def is_allowed_image(name: str) -> bool:
    return Path(name or "").suffix.lower() in _ALLOWED_IMAGE_SUFFIX
