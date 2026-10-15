"""v1 版本路由汇总。"""
from fastapi import APIRouter

from app.api.v1 import faces, persons, qrcode, recognition, system

api_router = APIRouter()
api_router.include_router(system.router)
api_router.include_router(persons.router)
api_router.include_router(faces.router)
api_router.include_router(recognition.router)
api_router.include_router(qrcode.router)

__all__ = ["api_router"]
