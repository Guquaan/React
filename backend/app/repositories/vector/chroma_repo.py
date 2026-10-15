"""ChromaDB 矢量库实现（默认后端）。

Chroma 的 cosine 空间返回的是距离 `distance = 1 - cosine`，
本类在内部统一换算成余弦相似度后再交给上层。
"""
from __future__ import annotations

import logging
from typing import Any, Sequence

import numpy as np

from app.core.config import Settings, get_settings
from app.core.errors import VectorStoreError
from app.repositories.vector.base import VectorHit, VectorRecord, VectorRepository

log = logging.getLogger(__name__)

_VALID_META = (str, int, float, bool)


class ChromaVectorRepository(VectorRepository):
    backend_name = "chroma"

    def __init__(self, settings: Settings | None = None) -> None:
        self.s = settings or get_settings()
        self._client = None
        self._collection = None
        self._error: str | None = None
        self._connect()

    # ------------------------------------------------------------------
    def _connect(self) -> None:
        try:
            import chromadb
            from chromadb.config import Settings as ChromaSettings

            self._client = chromadb.PersistentClient(
                path=str(self.s.vector_dir),
                settings=ChromaSettings(anonymized_telemetry=False, allow_reset=True),
            )
            self._collection = self._client.get_or_create_collection(
                name=self.s.vector_collection,
                metadata={"hnsw:space": "cosine"},
            )
            log.info("ChromaDB 就绪: %s (集合=%s)", self.s.vector_dir, self.s.vector_collection)
        except Exception as exc:  # noqa: BLE001
            self._error = f"{type(exc).__name__}: {exc}"
            log.warning("ChromaDB 初始化失败: %s", self._error)

    def is_ready(self) -> bool:
        return self._collection is not None

    @property
    def error(self) -> str | None:
        return self._error

    def _require(self):  # noqa: ANN202
        if self._collection is None:
            raise VectorStoreError(f"矢量库不可用: {self._error}")
        return self._collection

    @staticmethod
    def _clean_meta(meta: dict[str, Any]) -> dict[str, Any]:
        """Chroma 只接受 str/int/float/bool，其余转成字符串，None 直接剔除。"""
        out: dict[str, Any] = {}
        for k, v in (meta or {}).items():
            if v is None:
                continue
            out[k] = v if isinstance(v, _VALID_META) else str(v)
        return out

    # ------------------------------------------------------------------
    def upsert(self, records: Sequence[VectorRecord]) -> int:
        if not records:
            return 0
        col = self._require()
        col.upsert(
            ids=[r.id for r in records],
            embeddings=[np.asarray(r.embedding, dtype=np.float32).reshape(-1).tolist() for r in records],
            metadatas=[self._clean_meta(r.metadata) for r in records],
        )
        return len(records)

    def delete(self, ids: Sequence[str]) -> int:
        if not ids:
            return 0
        self._require().delete(ids=list(ids))
        return len(ids)

    def query(
        self,
        embedding: np.ndarray,
        top_k: int = 5,
        where: dict[str, Any] | None = None,
    ) -> list[VectorHit]:
        col = self._require()
        if col.count() == 0:
            return []
        res = col.query(
            query_embeddings=[np.asarray(embedding, dtype=np.float32).reshape(-1).tolist()],
            n_results=min(top_k, max(1, col.count())),
            where=self._clean_meta(where) if where else None,
            include=["metadatas", "distances"],
        )
        ids = (res.get("ids") or [[]])[0]
        dists = (res.get("distances") or [[]])[0]
        metas = (res.get("metadatas") or [[]])[0]
        hits: list[VectorHit] = []
        for i, vid in enumerate(ids):
            dist = float(dists[i]) if i < len(dists) else 1.0
            hits.append(
                VectorHit(
                    id=str(vid),
                    similarity=float(np.clip(1.0 - dist, -1.0, 1.0)),
                    metadata=dict(metas[i] or {}) if i < len(metas) else {},
                )
            )
        hits.sort(key=lambda h: h.similarity, reverse=True)
        return hits

    def get(self, ids: Sequence[str]) -> list[VectorHit]:
        if not ids:
            return []
        res = self._require().get(ids=list(ids), include=["metadatas"])
        got = res.get("ids") or []
        metas = res.get("metadatas") or []
        return [
            VectorHit(id=str(vid), similarity=1.0, metadata=dict(metas[i] or {}) if i < len(metas) else {})
            for i, vid in enumerate(got)
        ]

    def list_ids(self, where: dict[str, Any] | None = None) -> list[VectorHit]:
        res = self._require().get(
            where=self._clean_meta(where) if where else None, include=["metadatas"]
        )
        got = res.get("ids") or []
        metas = res.get("metadatas") or []
        return [
            VectorHit(id=str(vid), similarity=1.0, metadata=dict(metas[i] or {}) if i < len(metas) else {})
            for i, vid in enumerate(got)
        ]

    def count(self) -> int:
        if self._collection is None:
            return 0
        return int(self._collection.count())

    def reset(self) -> None:
        if self._client is None:
            return
        try:
            self._client.delete_collection(self.s.vector_collection)
        except Exception:  # noqa: BLE001
            pass
        self._collection = self._client.get_or_create_collection(
            name=self.s.vector_collection, metadata={"hnsw:space": "cosine"}
        )
