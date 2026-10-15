"""开发启动脚本：python run.py

等价于：uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
"""
from __future__ import annotations

import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


def main() -> None:
    import uvicorn

    from app.core.config import get_settings

    s = get_settings()
    uvicorn.run(
        "app.main:app",
        host=s.host,
        port=s.port,
        reload=(s.app_env == "dev"),
        reload_dirs=[str(BACKEND_DIR / "app")],
        log_level="info",
    )


if __name__ == "__main__":
    main()
