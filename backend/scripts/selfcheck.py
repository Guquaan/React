"""环境自检脚本：一条命令验证「配置 / 引擎 / 矢量库 / 评分 / 二维码 / 数据库」是否全部正常。

用法：
    python scripts/selfcheck.py
    python scripts/selfcheck.py --image path/to/face.jpg   # 顺带做一次真实特征提取
"""
from __future__ import annotations

import argparse
import sys
import traceback
from pathlib import Path

import numpy as np

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

PASS, FAIL, WARN = "✅", "❌", "⚠️ "
_results: list[tuple[str, str, str]] = []


def check(name: str, fn):  # noqa: ANN001, ANN201
    try:
        detail = fn()
        _results.append((PASS, name, str(detail or "")))
        return True
    except Exception as exc:  # noqa: BLE001
        _results.append((FAIL, name, f"{type(exc).__name__}: {exc}"))
        if "--verbose" in sys.argv:
            traceback.print_exc()
        return False


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", default="", help="可选：一张人脸照片路径")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    print("=" * 72)
    print(" FaceID 自检")
    print("=" * 72)

    # 1) 配置 & 目录
    def _config():
        from app.core.config import get_settings

        s = get_settings()
        s.ensure_dirs()
        return (
            f"engine={s.face_engine} vector={s.vector_backend} "
            f"cosine>={s.face_match_cosine_threshold} conf>={s.face_confidence_floor:.0%} "
            f"storage={s.storage_path}"
        )

    check("配置加载 / 目录创建", _config)

    # 2) 数据库
    def _db():
        from app.db import init_db, session_scope
        from app.repositories.person_repo import PersonRepository

        init_db()
        with session_scope() as db:
            n = PersonRepository(db).count()
        return f"建表成功，当前人员数 {n}"

    check("SQLite 关系库", _db)

    # 3) 引擎
    def _engine():
        from app.engines import get_engine

        e = get_engine()
        if not e.is_ready():
            raise RuntimeError(
                "引擎未就绪。请运行 python scripts/download_models.py，"
                "或在 .env 里设置 FACE_ENGINE=mock"
            )
        return f"{e.name} / {e.model_name}，维度 {e.dim}"

    engine_ok = check("人脸引擎加载", _engine)

    # 4) 矢量库
    def _vector():
        from app.repositories.vector import get_vector_repository

        repo = get_vector_repository()
        if not repo.is_ready():
            raise RuntimeError("矢量库不可用")
        rng = np.random.default_rng(42)
        a = rng.standard_normal(512).astype(np.float32)
        a /= np.linalg.norm(a)
        b = (a + rng.standard_normal(512).astype(np.float32) * 0.05)
        b /= np.linalg.norm(b)
        c = rng.standard_normal(512).astype(np.float32)
        c /= np.linalg.norm(c)

        from app.repositories.vector import VectorRecord

        ids = ["__selfcheck_a", "__selfcheck_b", "__selfcheck_c"]
        repo.upsert([
            VectorRecord(id=ids[0], embedding=a, metadata={"person_id": "__t"}),
            VectorRecord(id=ids[1], embedding=b, metadata={"person_id": "__t"}),
            VectorRecord(id=ids[2], embedding=c, metadata={"person_id": "__t"}),
        ])
        hits = repo.query(a, top_k=3)
        repo.delete(ids)
        top = hits[0].id if hits else "?"
        sim = hits[0].similarity if hits else -9
        if top != ids[0] or sim < 0.95:
            raise RuntimeError(f"读写校验失败，top={top} sim={sim:.4f}")
        repo.delete(ids)
        return f"{repo.backend_name}，写入/检索/删除全部正常（自相似 {sim:.4f}）"

    check("矢量数据库读写", _vector)

    # 5) 评分映射
    def _scoring():
        from app.services.scoring import to_confidence

        assert abs(to_confidence(0.40) - 0.70) < 1e-9, "cos=0.40 应映射为 0.70"
        assert to_confidence(1.0) == 1.0
        return "cos 0.40 -> 70%、1.00 -> 100% 映射正确"

    check("置信度映射（准确率对齐）", _scoring)

    # 6) 二维码加签
    def _qr():
        from app.core.config import get_settings
        from app.core.security import issue_token, parse_token

        s = get_settings()
        tok = issue_token({"pid": "abc"}, s.qr_secret_key)
        assert parse_token(tok, s.qr_secret_key).get("pid") == "abc"
        assert parse_token(tok + "x", s.qr_secret_key) == {}, "篡改后应校验失败"
        return "签发 / 校验 / 防篡改 正常"

    check("二维码签名", _qr)

    # 7) 真实图片（可选）
    if args.image:
        def _real():
            from app.engines import get_engine
            from app.utils.image import decode_image, resize_max

            img = resize_max(decode_image(Path(args.image).read_bytes()), 1280)
            e = get_engine()
            faces = e.detect_and_embed(img)
            if not faces:
                raise RuntimeError("未检测到人脸")
            f = faces[0]
            return (
                f"检测到 {len(faces)} 张脸，最大 {f.bbox[2] - f.bbox[0]}x{f.bbox[3] - f.bbox[1]}px，"
                f"质量分 {f.quality_score:.3f}，特征 {f.embedding.shape}"
            )

        check(f"真实图片推理（{Path(args.image).name}）", _real)
    elif engine_ok:
        _results.append((WARN, "真实图片推理", "未传入 --image，已跳过"))

    print()
    for mark, name, detail in _results:
        print(f" {mark} {name:<22} {detail}")
    print()

    failed = sum(1 for m, _, _ in _results if m == FAIL)
    print("=" * 72)
    print(f" 结果：{'全部通过 ✔' if failed == 0 else f'{failed} 项失败 ✖'}")
    print("=" * 72)
    raise SystemExit(1 if failed else 0)


if __name__ == "__main__":
    main()
