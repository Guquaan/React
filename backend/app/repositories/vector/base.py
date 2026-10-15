"""矢量数据库仓储的抽象接口（依赖倒置）。

services 层只认这个接口。默认用 ChromaDB 实现；
把 VECTOR_BACKEND 改成 local 就切换到内置 NumPy+SQLite 实现，业务代码不動。

约定：所有实现返回的 `similarity` 都是**余弦相似度**，范围 [-1, 1]，越大越像。
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Sequence

import numpy as np


@dataclass(slots=True)
class VectorRecord:
    """写入矢量库的一条记录。"""

    id: str
    embedding: np.ndarray
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class VectorHit:
    """检索命中的一条记录。"""

    id: str
    similarity: float
    metadata: dict[str, Any] = field(default_factory=dict)


class VectorRepository(ABC):
    """人脸特征向量仓储接口。"""

    backend_name: str = "abstract"

    # ---------------- 写 ----------------
    @abstractmethod
    def upsert(self, records: Sequence[VectorRecord]) -> int:
        """写入或覆盖，返回写入条数。"""

    @abstractmethod
    def delete(self, ids: Sequence[str]) -> int:
        """按主键删除，返回删除条数。"""

    def delete_where(self, where: dict[str, Any]) -> int:
        """按元数据删除（如按 person_id 清空某人所有样本）。"""
        ids = [h.id for h in self.list_ids(where)]
        return self.delete(ids) if ids else 0

    # ---------------- 读 ----------------
    @abstractmethod
    def query(
        self,
        embedding: np.ndarray,
        top_k: int = 5,
        where: dict[str, Any] | None = None,
    ) -> list[VectorHit]:
        """1:N 近邻检索。"""

    @abstractmethod
    def get(self, ids: Sequence[str]) -> list[VectorHit]:
        """按主键取回（similarity 填 1.0）。"""

    @abstractmethod
    def list_ids(self, where: dict[str, Any] | None = None) -> list[VectorHit]:
        """按条件列出全部主键（similarity 填 1.0），用于按人删除。"""

    # ---------------- 运维 ----------------
    @abstractmethod
    def count(self) -> int:
        """向量总数。"""

    @abstractmethod
    def is_ready(self) -> bool:
        """后端是否可用。"""

    def reset(self) -> None:  # pragma: no cover - 可选
        """清空整个集合（危险操作，仅供测试）。"""
        raise NotImplementedError

    # ---------------- 共享工具 ----------------
    @staticmethod
    def _to_matrix(records: Sequence[VectorRecord]) -> np.ndarray:
        return np.vstack([np.asarray(r.embedding, dtype=np.float32).reshape(1, -1) for r in records])
