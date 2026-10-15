"""ORM 模型 —— 只存"业务元数据 + 时间"，人脸特征向量存放在矢量库。

设计原则（对应"原子性强"）：
  Person         只管人的身份档案
  FaceSample     只管一张已注册的人脸样本（与矢量库中的一条向量 1:1 对应）
  RecognitionLog 只管一次识别事件（谁、多像、什么时候）
  QrScanLog      只管一次扫码事件（谁扫的、什么时候）
四张表职责互不重叠，任何一张表都可以独立演进。
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.utils.ids import new_id, new_person_code
from app.utils.time import utcnow


def _pk() -> str:
    return new_id()


class Person(Base):
    """人员档案。"""

    __tablename__ = "person"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_pk)
    person_code: Mapped[str] = mapped_column(String(16), unique=True, index=True, default=new_person_code)
    name: Mapped[str] = mapped_column(String(64), index=True)
    employee_no: Mapped[str | None] = mapped_column(String(64), unique=True, nullable=True, index=True)
    department: Mapped[str | None] = mapped_column(String(64), nullable=True)
    title: Mapped[str | None] = mapped_column(String(64), nullable=True)
    gender: Mapped[str | None] = mapped_column(String(8), nullable=True)   # male / female / unknown
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    email: Mapped[str | None] = mapped_column(String(128), nullable=True)
    remark: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    faces: Mapped[list["FaceSample"]] = relationship(
        back_populates="person", cascade="all, delete-orphan", lazy="selectin"
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Person {self.person_code} {self.name}>"


class FaceSample(Base):
    """已注册的人脸样本，与矢量库中的向量一一对应。"""

    __tablename__ = "face_sample"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_pk)
    person_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("person.id", ondelete="CASCADE"), index=True
    )

    # 矢量库中的主键，删除/更新时据此操作
    vector_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    engine: Mapped[str] = mapped_column(String(32))          # arcface / mock
    model_name: Mapped[str] = mapped_column(String(64))      # arcface_r50
    dim: Mapped[int] = mapped_column(Integer, default=512)

    image_path: Mapped[str] = mapped_column(String(512))     # 相对 storage 的路径
    is_primary: Mapped[bool] = mapped_column(default=False)  # 是否为展示主图

    # 质量指标：注册时用于筛选，识别时用于解释
    quality_score: Mapped[float] = mapped_column(Float, default=0.0)
    face_width: Mapped[int] = mapped_column(Integer, default=0)
    face_height: Mapped[int] = mapped_column(Integer, default=0)
    det_score: Mapped[float] = mapped_column(Float, default=0.0)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)

    person: Mapped[Person] = relationship(back_populates="faces")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<FaceSample {self.id} person={self.person_id}>"


class RecognitionLog(Base):
    """一次人脸识别事件（对应"看到人脸数据 + 时间"的需求）。"""

    __tablename__ = "recognition_log"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_pk)

    # 命中的人员（未命中为 NULL）
    person_id: Mapped[str | None] = mapped_column(
        String(32), ForeignKey("person.id", ondelete="SET NULL"), nullable=True, index=True
    )
    # 用于展示的快照字段（即人员被删除也保留历史可读性）
    person_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    person_code: Mapped[str | None] = mapped_column(String(16), nullable=True)

    matched_face_id: Mapped[str | None] = mapped_column(String(32), nullable=True)

    similarity: Mapped[float] = mapped_column(Float, default=0.0)   # 原始余弦相似度 [-1,1]
    confidence: Mapped[float] = mapped_column(Float, default=0.0)   # 归一化置信度 [0,1]
    is_matched: Mapped[bool] = mapped_column(default=False, index=True)
    threshold: Mapped[float] = mapped_column(Float, default=0.0)

    mode: Mapped[str] = mapped_column(String(16), default="identify")  # identify / verify
    source: Mapped[str] = mapped_column(String(16), default="web")     # web / api / camera
    snapshot_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    top_k_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    elapsed_ms: Mapped[float] = mapped_column(Float, default=0.0)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<RecognitionLog {self.id} matched={self.is_matched} conf={self.confidence:.2f}>"


class QrScanLog(Base):
    """一次二维码取数事件。"""

    __tablename__ = "qr_scan_log"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_pk)
    person_id: Mapped[str | None] = mapped_column(
        String(32), ForeignKey("person.id", ondelete="SET NULL"), nullable=True, index=True
    )
    person_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    token_digest: Mapped[str | None] = mapped_column(String(64), nullable=True)  # 只存摘要，不存原文
    is_valid: Mapped[bool] = mapped_column(default=True, index=True)
    client_ip: Mapped[str | None] = mapped_column(String(64), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(256), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
