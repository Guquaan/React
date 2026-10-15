"""人脸注册服务（业务核心之一）。

单张图片的注册流程被拆成 6 个可独立测试的步骤：
    decode -> detect -> select_best -> quality_gate -> embed -> persist
任何一步失败都只影响这一张图，不会污染其他人的数据（原子性）。
"""
from __future__ import annotations

import logging

import numpy as np
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import LowQualityFaceError, NoFaceDetectedError
from app.db.models import FaceSample
from app.engines import EmbeddingEngine, get_engine
from app.repositories.face_repo import FaceRepository
from app.repositories.person_repo import PersonRepository
from app.repositories.vector import VectorRecord, VectorRepository, get_vector_repository
from app.schemas.face import FaceRegisterResult, FaceSampleBrief
from app.services.scoring import should_accept_registration
from app.services.serializers import face_out
from app.services.storage_service import StorageService, get_storage
from app.utils.ids import new_id
from app.utils.image import crop_with_margin, decode_image, resize_max

log = logging.getLogger(__name__)


class FaceService:
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

    # ------------------------------------------------------------------
    # 公共入口
    # ------------------------------------------------------------------
    def register_from_images(
        self,
        person_id: str,
        uploads: list[tuple[str, bytes]],
        *,
        make_first_primary: bool = True,
    ) -> FaceRegisterResult:
        """批量注册（多张不同角度的照片能明显提高后续识别准确率）。"""
        person = self.persons.get(person_id)
        if person is None:
            from app.core.errors import NotFoundError

            raise NotFoundError(f"人员不存在: {person_id}")

        result = FaceRegisterResult()
        has_primary = any(f.is_primary for f in person.faces)

        for idx, (filename, data) in enumerate(uploads):
            want_primary = make_first_primary and not has_primary and idx == 0
            try:
                face = self.register_from_array(
                    person.id,
                    decode_image(data),
                    filename=filename,
                    is_primary=want_primary,
                )
                has_primary = has_primary or face.is_primary
                result.accepted += 1
                result.faces.append(
                    FaceSampleBrief(
                        id=face.id,
                        vector_id=face.vector_id,
                        image_url=self.storage.to_url(face.image_path) or "",
                        quality_score=round(float(face.quality_score), 4),
                        is_primary=face.is_primary,
                        created_at=face.created_at,
                    )
                )
                result.messages.append(f"「{filename}」注册成功（质量分 {face.quality_score:.2f}）")
            except (NoFaceDetectedError, LowQualityFaceError, ValueError) as exc:
                result.rejected += 1
                result.messages.append(f"「{filename}」被拒绝：{exc}")
                log.info("注册拒绝 person=%s file=%s reason=%s", person_id, filename, exc)
        return result

    def register_from_array(
        self,
        person_id: str,
        image: np.ndarray,
        *,
        filename: str = "upload.jpg",
        is_primary: bool = False,
    ) -> FaceSample:
        """单张 ndarray 注册；失败抛业务异常。"""
        image = resize_max(image, 1280)

        # 1) 检测
        detected = self.engine.detect(image)
        if not detected:
            raise NoFaceDetectedError("未检测到人脸，请上传清晰的正面照片")

        # 2) 选质量最好的一张（按面积 + 质量分）
        best = max(detected, key=lambda f: f.quality_score * 0.6 + min(f.area / 40000.0, 1.0) * 0.4)

        # 3) 质量闸门
        ok, reason = should_accept_registration(
            quality_score=best.quality_score,
            face_width=best.width,
            face_height=best.height,
            min_size=self.s.face_min_size,
        )
        if not ok:
            raise LowQualityFaceError(reason)

        # 4) 特征
        vec = self.engine.embed_one(image, best)

        # 5) 落盘（原图 + 人脸特写）
        original_rel = self.storage.save_bytes(
            _encode(image), subdir="faces/originals", filename=filename
        )
        crop_rel = self.storage.save_image(
            crop_with_margin(image, best.bbox), subdir="faces/crops", prefix="face"
        )

        # 6) 先写矢量库，成功后再写关系表；数据库失败则回收矢量，保证不留孤儿
        vector_id = f"vec_{new_id()}"
        self.vectors.upsert(
            [
                VectorRecord(
                    id=vector_id,
                    embedding=vec,
                    metadata={
                        "person_id": person_id,
                        "engine": self.engine.name,
                        "model_name": self.engine.model_name,
                        "dim": int(vec.size),
                        "original_path": original_rel,
                    },
                )
            ]
        )

        try:
            if is_primary:
                self.faces.clear_primary(person_id)
            face = self.faces.create(
                person_id=person_id,
                vector_id=vector_id,
                engine=self.engine.name,
                model_name=self.engine.model_name,
                dim=int(vec.size),
                image_path=crop_rel,
                is_primary=is_primary,
                quality_score=float(best.quality_score),
                face_width=int(best.width),
                face_height=int(best.height),
                det_score=float(best.det_score),
            )
            self.db.commit()
        except Exception:
            self.db.rollback()
            self.vectors.delete([vector_id])
            self.storage.remove(crop_rel)
            self.storage.remove(original_rel)
            raise

        log.info(
            "人脸注册成功 person=%s face=%s quality=%.3f size=%dx%d",
            person_id, face.id, best.quality_score, best.width, best.height,
        )
        return face

    # ------------------------------------------------------------------
    def delete_face(self, face_id: str) -> None:
        face = self.faces.get(face_id)
        if face is None:
            from app.core.errors import NotFoundError

            raise NotFoundError(f"人脸样本不存在: {face_id}")

        person_id, was_primary = face.person_id, face.is_primary
        vector_id, image_path = face.vector_id, face.image_path

        self.faces.delete(face)
        self.vectors.delete([vector_id])

        # 若删除的是主图，则把剩下最早的一张提升为主图
        if was_primary:
            rest = self.faces.list_by_person(person_id)
            if rest:
                self.faces.clear_primary(person_id)
                rest[-1].is_primary = True
        self.db.commit()
        self.storage.remove(image_path)
        log.info("删除人脸样本 face=%s person=%s", face_id, person_id)

    def sync_vectors(self) -> dict[str, int]:
        """对账：清理矢量库中已无对应 DB 记录的孤儿向量。"""
        db_vector_ids = set(self.faces.all_vector_ids())
        stored = {h.id for h in self.vectors.list_ids()}
        orphans = sorted(stored - db_vector_ids)
        if orphans:
            self.vectors.delete(orphans)
        return {"vector_total": len(stored), "orphans_removed": len(orphans)}

    def clear_person_vectors(self, person_id: str) -> int:
        return self.vectors.delete_where({"person_id": person_id})


def _encode(img: np.ndarray, quality: int = 92) -> bytes:
    from app.utils.image import encode_jpeg

    return encode_jpeg(img, quality=quality)
