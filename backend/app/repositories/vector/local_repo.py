"""内置矢量库实现（零外部依赖兜底方案）。

向量以 float32 blob 存在独立的 SQLite 文件里，检索时做精确（暴力）余弦相似度。
在几千~几万条样本量级下延迟仍在毫秒级，且完全不需要 Docker / 服务端。

存在的意义：
  1. chromadb 安装失败或环境受限时，项目依然能完整跑通；
  2. 与 ChromaVectorRepository 实现同一接口，用来做交叉验证。
"""
from __future__ import annotations

import json
import logging
import sqlite3
from typing import Any, Sequence

import numpy as np

from app.core.config import Settings, get_settings
from app.core.errors import VectorStoreError
from app.repositories.vector.base import VectorHit, VectorRecord, VectorRepository

log = logging.getLogger(__name__)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS vector_store (
    id        TEXT PRIMARY KEY,
    dim       INTEGER NOT NULL,
    embedding BLOB    NOT NULL,
    metadata  TEXT    NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_vector_store_person
    ON vector_store (json_extract(metadata, '$.person_id'));
"""


class LocalVectorRepository(VectorRepository):
    backend_name = "local"

    def __init__(self, settings: Settings | None = None) -> None:
        self.s = settings or get_settings()
        self._db_path = self.s.vector_dir / "local_vectors.db"
        self._ok = False
        try:
            self._db_path.parent.mkdir(parents=True, exist_ok=True)
            with self._conn() as conn:
                conn.executescript(_SCHEMA)
            self._ok = True
            log.info("内置矢量库就绪: %s", self._db_path)
        except Exception as exc:  # noqa: BLE001
            log.warning("内置矢量库初始化失败: %s", exc)

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self._db_path), timeout=15)
        conn.row_factory = sqlite3.Row
        return conn

    def is_ready(self) -> bool:
        return self._ok

    def _require(self) -> None:
        if not self._ok:
            raise VectorStoreError(f"内置矢量库不可用: {self._db_path}")

    # ------------------------------------------------------------------
    def upsert(self, records: Sequence[VectorRecord]) -> int:
        if not records:
            return 0
        self._require()
        rows = [
            (
                r.id,
                int(np.asarray(r.embedding).size),
                np.asarray(r.embedding, dtype=np.float32).reshape(-1).tobytes(),
                json.dumps(r.metadata or {}, ensure_ascii=False, default=str),
            )
            for r in records
        ]
        with self._conn() as conn:
            conn.executemany(
                "INSERT INTO vector_store (id, dim, embedding, metadata) VALUES (?,?,?,?) "
                "ON CONFLICT(id) DO UPDATE SET dim=excluded.dim, embedding=excluded.embedding, metadata=excluded.metadata",
                rows,
            )
        return len(rows)

    def delete(self, ids: Sequence[str]) -> int:
        if not ids:
            return 0
        self._require()
        marks = ",".join("?" * len(ids))
        with self._conn() as conn:
            cur = conn.execute(f"DELETE FROM vector_store WHERE id IN ({marks})", list(ids))
        return int(cur.rowcount or 0)

    def _all(self, where: dict[str, Any] | None = None) -> list[VectorHit]:
        self._require()
        with self._conn() as conn:
            rows = conn.execute("SELECT id, embedding, metadata FROM vector_store").fetchall()
        hits: list[VectorHit] = []
        for row in rows:
            meta = json.loads(row["metadata"] or "{}")
            if where and any(meta.get(k) != v for k, v in where.items()):
                continue
            hits.append(VectorHit(id=row["id"], similarity=1.0, metadata=meta))
        return hits

    def get(self, ids: Sequence[str]) -> list[VectorHit]:
        if not ids:
            return []
        wanted = set(ids)
        return [h for h in self._all() if h.id in wanted]

    def list_ids(self, where: dict[str, Any] | None = None) -> list[VectorHit]:
        return self._all(where)

    def count(self) -> int:
        if not self._ok:
            return 0
        with self._conn() as conn:
            return int(conn.execute("SELECT COUNT(*) FROM vector_store").fetchone()[0])

    def query(
        self,
        embedding: np.ndarray,
        top_k: int = 5,
        where: dict[str, Any] | None = None,
    ) -> list[VectorHit]:
        self._require()
        q = np.asarray(embedding, dtype=np.float32).reshape(-1)
        qn = float(np.linalg.norm(q)) or 1.0
        q = q / qn

        with self._conn() as conn:
            rows = conn.execute("SELECT id, embedding, metadata FROM vector_store").fetchall()
        if not rows:
            return []

        ids: list[str] = []
        metas: list[dict] = []
        mats: list[np.ndarray] = []
        for row in rows:
            meta = json.loads(row["metadata"] or "{}")
            if where and any(meta.get(k) != v for k, v in where.items()):
                continue
            ids.append(row["id"])
            metas.append(meta)
            mats.append(np.frombuffer(row["embedding"], dtype=np.float32))
        if not mats:
            return []

        mat = np.vstack(mats)
        norms = np.linalg.norm(mat, axis=1)
        norms[norms == 0] = 1.0
        sims = (mat / norms[:, None]) @ q

        order = np.argsort(-sims)[: max(1, top_k)]
        return [
            VectorHit(id=ids[i], similarity=float(np.clip(sims[i], -1.0, 1.0)), metadata=metas[i])
            for i in order
        ]

    def reset(self) -> None:
        if not self._ok:
            return
        with self._conn() as conn:
            conn.execute("DELETE FROM vector_store")
