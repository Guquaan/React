"""一键灌入演示数据。

用法：
    python scripts/seed_demo.py              # 只建人员档案（无照片）
    python scripts/seed_demo.py --images     # 同时把 backend/dataset/<person>/ 下的照片注册为人脸样本

配合 fetch_sample_dataset.py 使用即可得到一个可以直接演示的系统：
    python scripts/fetch_sample_dataset.py
    python scripts/download_models.py
    python scripts/seed_demo.py --images
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

IMAGE_SUFFIX = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}

# 目录名 -> 中文姓名 / 档案信息
PROFILE_MAP: dict[str, dict] = {
    "obama": {"name": "示例人员A", "department": "研发部", "title": "算法工程师", "gender": "male"},
    "biden": {"name": "示例人员B", "department": "产品部", "title": "产品经理", "gender": "male"},
    "kit_harington": {"name": "示例人员C", "department": "研发部", "title": "后端工程师", "gender": "male"},
    "alex_lacamoire": {"name": "示例人员D", "department": "设计部", "title": "视觉设计师", "gender": "male"},
    "rose_leslie": {"name": "示例人员E", "department": "人事部", "title": "HRBP", "gender": "female"},
}

FALLBACK_PERSONS = [
    {"name": "张伟", "department": "研发部", "title": "前端工程师", "gender": "male"},
    {"name": "李娜", "department": "研发部", "title": "测试工程师", "gender": "female"},
    {"name": "王强", "department": "产品部", "title": "产品经理", "gender": "male"},
    {"name": "赵敏", "department": "人事部", "title": "HRBP", "gender": "female"},
    {"name": "陈晨", "department": "运营部", "title": "运营专员", "gender": "female"},
]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--images", action="store_true", help="同时注册 dataset 下的照片")
    parser.add_argument("--dataset", default=str(BACKEND_DIR / "dataset"))
    args = parser.parse_args()

    from app.core.config import get_settings
    from app.db import init_db, session_scope
    from app.repositories.face_repo import FaceRepository
    from app.repositories.person_repo import PersonRepository
    from app.schemas.person import PersonCreate
    from app.services import FaceService, PersonService

    s = get_settings()
    s.ensure_dirs()
    init_db()

    dataset_root = Path(args.dataset)
    folders = (
        [d for d in sorted(dataset_root.iterdir()) if d.is_dir() and any(
            f.suffix.lower() in IMAGE_SUFFIX for f in d.iterdir()
        )]
        if dataset_root.exists()
        else []
    )

    profiles: list[dict] = []
    for folder in folders:
        profile = dict(PROFILE_MAP.get(folder.name, {}))
        profile.setdefault("name", folder.name)
        profile.setdefault("department", "未分组")
        profiles.append({**profile, "_folder": str(folder)})

    if not profiles:
        profiles = [{**p, "_folder": None} for p in FALLBACK_PERSONS]

    created, skipped, face_ok, face_bad = 0, 0, 0, 0

    for idx, profile in enumerate(profiles, start=1):
        folder = profile.pop("_folder", None)
        employee_no = f"EMP{idx:04d}"

        with session_scope() as db:
            persons = PersonRepository(db)
            if persons.get_by_employee_no(employee_no):
                skipped += 1
                continue
            svc = PersonService(db)
            out = svc.create(PersonCreate(employee_no=employee_no, **profile))
            person_id = out.id
            print(f"  + 人员 {out.person_code}  {profile['name']}（{profile.get('department')}）")
            created += 1

        if args.images and folder:
            images = [
                (f.name, f.read_bytes())
                for f in sorted(Path(folder).iterdir())
                if f.suffix.lower() in IMAGE_SUFFIX
            ]
            with session_scope() as db:
                svc = FaceService(db)
                result = svc.register_from_images(person_id, images)
                face_ok += result.accepted
                face_bad += result.rejected
                for msg in result.messages:
                    print(f"      {msg}")

    print("-" * 62)
    print(f"人员：新建 {created}，跳过（已存在）{skipped}")
    if args.images:
        print(f"人脸样本：注册成功 {face_ok}，被拒绝 {face_bad}")
    print("\n下一步：python run.py  然后在浏览器打开 http://127.0.0.1:8000/docs")


if __name__ == "__main__":
    main()
