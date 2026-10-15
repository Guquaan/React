"""人脸识别服务（业务核心之二）：1:N 识别 + 1:1 比对。

流程被拆成可独立替换的步骤：
    detect -> embed -> vector_search -> judge -> persist_log
判定规则全部来自 `scoring` 模块，本类只做编排，不含魔法数字。
"""
from __future__ import annotations

import json
import logging
import time

import numpy as np
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import NoFaceDetectedError
from app.db.models import RecognitionLog
from app.engines import EmbeddingEngine, get_engine
from app.repositories.face_repo import FaceRepository
from app.repositories.log_repo import LogRepository
from app.repositories.person_repo import PersonRepository
from app.repositories.vector import VectorRepository, get_vector_repository
from app.schemas.face import IdentifyResult, MatchCandidate, VerifyResult
from app.services.scoring import is_match, to_confidence
from app.services.serializers import person_brief
from app.services.storage_service import StorageService, get_storage
from app.utils.image import resize_max

log = logging.getLogger(__name__)


class RecognitionService:
    def __init__(
        self,
        db: Session,
        *,
        engine: EmbeddingEngine | None = None,
        vectors: VectorRepository | None = None,
        storage: StorageService | None = None,
    ) -> None:
        self.db = db
        self.s = get_settings()
        self.engine = engine or get_engine()
        self.vectors = vectors or get_vector_repository()
        self.storage = storage or get_storage()
        self.persons = PersonRepository(db)
        self.faces = FaceRepository(db)
        self.logs = LogRepository(db)

    @property
    def threshold(self) -> float:
        """余弦判定阈值；若配置的置信度底线更高，则以换算后的余弦为准。"""
        from app.services.scoring import confidence_to_cosine

        return max(float(self.s.face_match_cosine_threshold), confidence_to_cosine(self.s.face_confidence_floor))

    # ------------------------------------------------------------------
    # 1:N 识别
    # ------------------------------------------------------------------
    def identify(
        self,
        image: np.ndarray,
        *,
        top_k: int | None = None,
        source: str = "web",
        save_snapshot: bool = True,
    ) -> IdentifyResult:
        t0 = time.perf_counter()
        image = resize_max(image, 1280)

        detected = self.engine.detect(image)
        if not detected:
            raise NoFaceDetectedError("未检测到人脸，请调整角度或光线后重试")

        target = detected[0]  # detect() 已按面积降序
        vec = self.engine.embed_one(image, target)

        k = int(top_k or self.s.face_match_top_k)
        hits = self.vectors.query(vec, top_k=k)

        candidates = self._build_candidates(hits)
        best = candidates[0] if candidates else None
        matched = bool(best and best.passed)

        snapshot_rel = self.storage.save_snapshot(image) if save_snapshot else None
        elapsed_ms = (time.perf_counter() - t0) * 1000.0

        person = self.persons.get(best.person_id) if matched and best else None

        row = self.logs.add_recognition(
            person_id=person.id if person else None,
            person_name=person.name if person else (best.person_name if best else None),
            person_code=person.person_code if person else (best.person_code if best else None),
            matched_face_id=(self._face_id_of(best) if best else None),
            similarity=float(best.similarity) if best else 0.0,
            confidence=float(best.confidence) if best else 0.0,
            is_matched=matched,
            threshold=self.threshold,
            mode="identify",
            source=source,
            snapshot_path=snapshot_rel,
            top_k_json=json.dumps(
                [
                    {
                        "person_id": c.person_id,
                        "person_name": c.person_name,
                        "similarity": round(c.similarity, 4),
                        "confidence": round(c.confidence, 4),
                        "passed": c.passed,
                    }
                    for c in candidates
                ],
                ensure_ascii=False,
            ),
            elapsed_ms=elapsed_ms,
        )
        self.db.commit()

        log.info(
            "识别完成 matched=%s person=%s sim=%.4f conf=%.4f 耗时=%.1fms 候选=%d",
            matched,
            person.name if person else "-",
            best.similarity if best else 0.0,
            best.confidence if best else 0.0,
            elapsed_ms,
            len(candidates),
        )

        return IdentifyResult(
            matched=matched,
            threshold=self.threshold,
            confidence_floor=float(self.s.face_confidence_floor),
            elapsed_ms=round(elapsed_ms, 2),
            face_count=len(detected),
            best=best,
            candidates=candidates,
            person=person_brief(person) if person else None,
            recognized_at=row.created_at,
            log_id=row.id,
            snapshot_url=self.storage.to_url(snapshot_rel),
        )

    # ------------------------------------------------------------------
    # 1:1 比对
    # ------------------------------------------------------------------
    def verify(
        self,
        person_id: str,
        image: np.ndarray,
        *,
        source: str = "web",
        save_snapshot: bool = True,
    ) -> VerifyResult:
        from app.core.errors import NotFoundError

        t0 = time.perf_counter()
        person = self.persons.get(person_id)
        if person is None:
            raise NotFoundError(f"人员不存在: {person_id}")

        image = resize_max(image, 1280)
        detected = self.engine.detect(image)
        if not detected:
            raise NoFaceDetectedError("未检测到人脸，请调整角度或光线后重试")

        target = detected[0]
        vec = self.engine.embed_one(image, target)

        # 取该人所有注册样本中的最高相似度（max pooling 提升召回）
        sample_count = max(1, len(self.faces.list_by_person(person_id)))
        hits = self.vectors.query(vec, top_k=sample_count, where={"person_id": person_id})
        sims = [h.similarity for h in hits]

        similarity = max(sims) if sims else -1.0
        confidence = to_confidence(similarity)
        matched = bool(sims) and is_match(similarity, self.threshold)
        elapsed_ms = (time.perf_counter() - t0) * 1000.0

        snapshot_rel = self.storage.save_snapshot(image) if save_snapshot else None

        row = self.logs.add_recognition(
            person_id=person.id,
            person_name=person.name,
            person_code=person.person_code,
            matched_face_id=None,
            similarity=float(similarity),
            confidence=float(confidence),
            is_matched=matched,
            threshold=self.threshold,
            mode="verify",
            source=source,
            snapshot_path=snapshot_rel,
            top_k_json=json.dumps(
                [{"person_id": person.id, "similarity": round(similarity, 4), "passed": matched}],
                ensure_ascii=False,
            ),
            elapsed_ms=elapsed_ms,
        )
        self.db.commit()

        return VerifyResult(
            matched=matched,
            similarity=round(float(similarity), 4),
            confidence=round(float(confidence), 4),
            threshold=self.threshold,
            confidence_floor=float(self.s.face_confidence_floor),
            elapsed_ms=round(elapsed_ms, 2),
            person=person_brief(person),
            recognized_at=row.created_at,
            message="比对通过，属于同一人" if matched else "比对未通过，相似度低于阈值",
        )

    # ------------------------------------------------------------------
    def _build_candidates(self, hits: list) -> list[MatchCandidate]:
        out: list[MatchCandidate] = []
        threshold = self.threshold
        seen_persons: set[str] = set()
        for hit in hits:
            pid = str(hit.metadata.get("person_id") or "")
            if not pid:
                continue
            face = self.faces.get_by_vector_id(hit.id)
            person = self.persons.get(pid)
            if person is None:
                continue

            # 同一人多个样本时只保留最像的那条，避免候选列表被同一个人刷屏
            if pid in seen_persons:
                continue
            seen_persons.add(pid)

            out.append(
                MatchCandidate(
                    person_id=pid,
                    person_code=person.person_code,
                    person_name=person.name,
                    department=person.department,
                    face_id=face.id if face else None,
                    image_url=self.storage.to_url(face.image_path) if face else None,
                    similarity=round(float(hit.similarity), 4),
                    confidence=round(to_confidence(hit.similarity), 4),
                    passed=is_match(hit.similarity, threshold),
                )
            )
            if len(out) >= 5:
                break
        return out

    def _face_id_of(self, candidate: MatchCandidate | None) -> str | None:
        return candidate.face_id if candidate else None
