"""人员管理路由。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.api.deps import person_service
from app.schemas.common import ApiResponse, Page
from app.schemas.person import PersonCreate, PersonDetail, PersonUpdate, PersonOut
from app.services import PersonService

router = APIRouter(prefix="/persons", tags=["人员管理"])


@router.post("", response_model=ApiResponse[PersonOut], summary="新建人员档案")
def create_person(payload: PersonCreate, svc: PersonService = Depends(person_service)):
    return ApiResponse(data=svc.create(payload), message="人员创建成功")


@router.get("", response_model=ApiResponse[Page[PersonOut]], summary="人员分页列表")
def list_persons(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    keyword: str | None = Query(None, description="姓名 / 编号 / 工号 / 部门 模糊搜索"),
    department: str | None = Query(None),
    svc: PersonService = Depends(person_service),
):
    items, meta = svc.list(page=page, page_size=page_size, keyword=keyword, department=department)
    return ApiResponse(data=Page[PersonOut](items=items, meta=meta))


@router.get("/departments", response_model=ApiResponse[list[str]], summary="部门列表")
def list_departments(svc: PersonService = Depends(person_service)):
    return ApiResponse(data=svc.departments())


@router.get("/code/{person_code}", response_model=ApiResponse[PersonDetail], summary="按人员编号查询")
def get_person_by_code(person_code: str, svc: PersonService = Depends(person_service)):
    return ApiResponse(data=svc.get_by_code(person_code))


@router.get("/{person_id}", response_model=ApiResponse[PersonDetail], summary="人员详情（含人脸样本与识别时间）")
def get_person(person_id: str, svc: PersonService = Depends(person_service)):
    return ApiResponse(data=svc.get(person_id))


@router.patch("/{person_id}", response_model=ApiResponse[PersonOut], summary="更新人员档案")
def update_person(
    person_id: str, payload: PersonUpdate, svc: PersonService = Depends(person_service)
):
    return ApiResponse(data=svc.update(person_id, payload), message="更新成功")


@router.delete("/{person_id}", response_model=ApiResponse[dict], summary="删除人员（级联清理人脸与向量）")
def delete_person(person_id: str, svc: PersonService = Depends(person_service)):
    return ApiResponse(data=svc.delete(person_id), message="删除成功")
