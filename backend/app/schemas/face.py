"""人脸注册 / 识别 DTO。"""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class DetectedFaceOut(BaseModel):
    """引擎检测到的单张人脸。"""

    bbox: tuple[int, int, int, int]
    det_score: float
    quality_score: float


class FaceRegisterResult(BaseModel):
    """一张图片的注册结果。"""

    accepted: int = 0
    rejected: int = 0
    faces: list["FaceSampleBrief"] = Field(default_factory=list)
    messages: list[str] = Field(default_factory=list)


class FaceSampleBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    vector_id: str
    image_url: str
    quality_score: float
    is_primary: bool
    created_at: datetime


class MatchCandidate(BaseModel):
    """1:N 检索的一个候选。"""

    person_id: str
    person_code: str
    person_name: str
    department: str | None = None
    face_id: str | None = None
    image_url: str | None = None
    similarity: float          # 原始余弦相似度
    confidence: float          # 归一化置信度 [0,1]
    passed: bool               # 是否 >= 阈值


class IdentifyResult(BaseModel):
    """1:N 识别结果。"""

    matched: bool
    threshold: float
    confidence_floor: float
    elapsed_ms: float
    face_count: int
    best: MatchCandidate | None = None
    candidates: list[MatchCandidate] = Field(default_factory=list)
    person: "PersonBriefOut | None" = None
    recognized_at: datetime
    log_id: str | None = None
    snapshot_url: str | None = None


class PersonBriefOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    person_code: str
    name: str
    employee_no: str | None = None
    department: str | None = None
    title: str | None = None
    gender: str | None = None
    phone: str | None = None
    email: str | None = None
    remark: str | None = None
    face_count: int = 0
    primary_image_url: str | None = None
    created_at: datetime


class VerifyResult(BaseModel):
    """1:1 比对结果。"""

    matched: bool
    similarity: float
    confidence: float
    threshold: float
    confidence_floor: float
    elapsed_ms: float
    person: PersonBriefOut | None = None
    recognized_at: datetime
    message: str = ""


IdentifyResult.model_rebuild()
