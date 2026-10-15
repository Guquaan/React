"""抓取公开示例人脸数据集（用于跑通准确率基准测试）。

数据来源：GitHub 上的开源示例图片（ageitgey/face_recognition 仓库）。
这些是公开人物照片，仅用于本地教学演示。

用法：
    python scripts/fetch_sample_dataset.py
    python scripts/benchmark_accuracy.py

生成结构：
    backend/dataset/
        obama/        （多张，用于拉开样本量）
        biden/
        kit_harington/
        alex_lacamoire/
        rose_leslie/
"""
from __future__ import annotations

import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

RAW = "https://raw.githubusercontent.com/ageitgey/face_recognition/master/examples"

# 每人一组公开图片 URL
MANIFEST: dict[str, list[str]] = {
    "obama": [
        f"{RAW}/obama.jpg",
        f"{RAW}/obama2.jpg",
        f"{RAW}/obama-240p.jpg",
        f"{RAW}/obama-480p.jpg",
        f"{RAW}/obama-720p.jpg",
        f"{RAW}/obama-1080p.jpg",
        f"{RAW}/knn_examples/test/obama1.jpg",
    ],
    "biden": [
        f"{RAW}/knn_examples/train/biden/biden.jpg",
        f"{RAW}/knn_examples/train/biden/biden2.jpg",
    ],
    "kit_harington": [
        f"{RAW}/knn_examples/train/kit_harington/john1.jpeg",
        f"{RAW}/knn_examples/train/kit_harington/john2.jpeg",
        f"{RAW}/knn_examples/test/johnsnow_test1.jpg",
    ],
    "alex_lacamoire": [
        f"{RAW}/knn_examples/train/alex_lacamoire/img1.jpg",
    ],
    "rose_leslie": [
        f"{RAW}/knn_examples/train/rose_leslie/img1.jpg",
        f"{RAW}/knn_examples/train/rose_leslie/img2.jpg",
    ],
}


def main() -> None:
    import httpx

    root = Path(sys.argv[1]) if len(sys.argv) > 1 else (BACKEND_DIR / "dataset")
    root.mkdir(parents=True, exist_ok=True)

    total_ok = total_fail = 0
    with httpx.Client(follow_redirects=True, timeout=45.0) as client:
        for person, urls in MANIFEST.items():
            out_dir = root / person
            out_dir.mkdir(parents=True, exist_ok=True)
            for idx, url in enumerate(urls, start=1):
                suffix = Path(url).suffix or ".jpg"
                target = out_dir / f"{idx:02d}{suffix}"
                if target.exists() and target.stat().st_size > 2000:
                    print(f"  · 已存在 {person}/{target.name}")
                    total_ok += 1
                    continue
                try:
                    resp = client.get(url)
                    resp.raise_for_status()
                    target.write_bytes(resp.content)
                    print(f"  ✔ {person}/{target.name}  {len(resp.content) / 1024:.0f}KB")
                    total_ok += 1
                except Exception as exc:  # noqa: BLE001
                    print(f"  ✖ {person}/{target.name} 失败: {type(exc).__name__} {exc}")
                    total_fail += 1

    print("-" * 60)
    print(f"完成：成功 {total_ok} 张，失败 {total_fail} 张")
    print(f"数据集目录：{root}")
    if total_ok:
        print("\n下一步：python scripts/benchmark_accuracy.py")


if __name__ == "__main__":
    main()
