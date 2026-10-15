"""人员相关 DTO。"""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class PersonBase(BaseModel):
    name: str = Field(min_length=1, max_length=64, description="姓名")
    employee_no: str | None = Field(default=None, max_length=64, description="工号/学号")
    department: str | None = Field(default=None, max_length=64)
    title: str | None = Field(default=None, max_length=64)
    gender: str | None = Field(default=None, pattern="^(male|female|unknown)?$")
    phone: str | None = Field(default=None, max_length=32)
    email: str | None = Field(default=None, max_length=128)
    remark: str | None = Field(default=None, max_length=1000)


class PersonCreate(PersonBase):
    pass


class PersonUpdate(BaseModel):
    """全部字段可选，实现 PATCH 语义。"""

    name: str | None = Field(default=None, min_length=1, max_length=64)
    employee_no: str | None = Field(default=None, max_length=64)
    department: str | None = Field(default=None, max_length=64)
    title: str | None = Field(default=None, max_length=64)
    gender: str | None = Field(default=None, pattern="^(male|female|unknown)?$")
    phone: str | None = Field(default=None, max_length=32)
    email: str | None = Field(default=None, max_length=128)
    remark: str | None = Field(default=None, max_length=1000)


class FaceSampleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    person_id: str
    vector_id: str
    engine: str
    model_name: str
    dim: int
    is_primary: bool
    image_url: str
    quality_score: float
    face_width: int
    face_height: int
    det_score: float
    created_at: datetime


class PersonOut(PersonBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    person_code: str
    face_count: int = 0
    primary_image_url: str | None = None
    created_at: datetime
    updated_at: datetime


class PersonDetail(PersonOut):
    faces: list[FaceSampleOut] = Field(default_factory=list)
    last_recognition_at: datetime | None = None
    recognition_count: int = 0
