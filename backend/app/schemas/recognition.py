"""识别记录 / 二维码 / 统计 DTO。"""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

# ============================ 识别记录 ============================


class RecognitionLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    person_id: str | None = None
    person_name: str | None = None
    person_code: str | None = None
    matched_face_id: str | None = None
    similarity: float
    confidence: float
    is_matched: bool
    threshold: float
    mode: str
    source: str
    snapshot_url: str | None = None
    elapsed_ms: float
    created_at: datetime


class RecognitionLogDetail(RecognitionLogOut):
    top_k: list[dict] = Field(default_factory=list)
    person_image_url: str | None = None


# ============================ 二维码 ============================


class QrPayloadOut(BaseModel):
    person_id: str
    person_code: str
    name: str
    token: str
    scan_url: str = Field(description="扫码后可直接打开的前端地址")
    resolve_url: str = Field(description="后端解析接口地址")
    expires_at: datetime | None = None
    generated_at: datetime


class QrResolveOut(BaseModel):
    valid: bool
    person: dict | None = None
    faces: list[dict] = Field(default_factory=list)
    recent_recognitions: list[RecognitionLogOut] = Field(default_factory=list)
    scanned_at: datetime
    message: str = ""


class QrScanLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    person_id: str | None = None
    person_name: str | None = None
    is_valid: bool
    client_ip: str | None = None
    created_at: datetime


# ============================ 统计 ============================


class NameCount(BaseModel):
    name: str
    count: int


class DateCount(BaseModel):
    date: str
    total: int
    matched: int


class StatsOverview(BaseModel):
    person_count: int
    face_count: int
    recognition_total: int
    recognition_matched: int
    recognition_today: int
    match_rate: float
    avg_confidence: float
    avg_elapsed_ms: float
    qr_scan_total: int
    vector_backend: str
    face_engine: str
    cosine_threshold: float
    confidence_floor: float
    department_distribution: list[NameCount] = Field(default_factory=list)
    trend_7d: list[DateCount] = Field(default_factory=list)
    top_recognized: list[NameCount] = Field(default_factory=list)
