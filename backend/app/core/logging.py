"""日志配置（幂等，可重复调用）。"""
from __future__ import annotations

import logging
import sys

_CONFIGURED = False
_FMT = "%(asctime)s | %(levelname)-7s | %(name)-28s | %(message)s"


def setup_logging(level: str = "INFO") -> None:
    global _CONFIGURED
    if _CONFIGURED:
        return

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(_FMT, datefmt="%H:%M:%S"))

    root = logging.getLogger()
    root.setLevel(level.upper())
    root.handlers = [handler]

    # 第三方库降噪
    for noisy in ("chromadb", "httpx", "httpcore", "uvicorn.access", "onnxruntime"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
