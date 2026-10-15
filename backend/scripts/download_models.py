"""模型下载脚本。

用法（在 backend/ 目录下执行）：

    # 默认：YuNet 检测器 + ArcFace-MobileFaceNet 识别器（共约 16MB，推荐）
    python scripts/download_models.py

    # 高精度：ArcFace-ResNet50 识别器（约 290MB，准确率更高）
    python scripts/download_models.py --variant l

    # 网络受限时用 GitHub 加速镜像
    python scripts/download_models.py --mirror https://ghfast.top/

下载完成后模型统一放在 backend/storage/models/ 下：
    face_detection_yunet_2023mar.onnx   人脸检测
    w600k_mbf.onnx / w600k_r50.onnx     人脸特征提取（512 维）
"""
from __future__ import annotations

import argparse
import io
import sys
import zipfile
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.config import get_settings  # noqa: E402

YUNET_URL = (
    "https://github.com/opencv/opencv_zoo/raw/main/models/"
    "face_detection_yunet/face_detection_yunet_2023mar.onnx"
)
INSIGHTFACE_RELEASE = "https://github.com/deepinsight/insightface/releases/download/v0.7"
VARIANTS = {
    "sc": ("buffalo_sc.zip", "w600k_mbf.onnx", 15),
    "l": ("buffalo_l.zip", "w600k_r50.onnx", 289),
}


def _human(n: int) -> str:
    return f"{n / 1024 / 1024:.1f}MB"


def _download(url: str, desc: str, timeout: float = 60.0) -> bytes:
    import httpx

    print(f"  ↓ {desc}\n    {url}")
    buf = bytearray()
    with httpx.Client(follow_redirects=True, timeout=timeout) as client:
        with client.stream("GET", url) as resp:
            resp.raise_for_status()
            total = int(resp.headers.get("content-length") or 0)
            last = -1
            for chunk in resp.iter_bytes(chunk_size=1 << 16):
                buf.extend(chunk)
                if total:
                    pct = int(len(buf) * 100 / total)
                    if pct != last and pct % 10 == 0:
                        last = pct
                        print(f"      进度 {pct:3d}%  ({_human(len(buf))})", end="\r", flush=True)
    print(f"      完成 {_human(len(buf))}          ")
    return bytes(buf)


def fetch_detector(models_dir: Path, mirror: str) -> Path:
    target = models_dir / "face_detection_yunet_2023mar.onnx"
    if target.exists() and target.stat().st_size > 100_000:
        print(f"✔ 检测模型已存在，跳过：{target.name}")
        return target
    data = _download(mirror + YUNET_URL, "YuNet 人脸检测模型（OpenCV Zoo，约 230KB）")
    target.write_bytes(data)
    print(f"✔ 已保存 {target}")
    return target


def fetch_recognizer(models_dir: Path, variant: str, mirror: str) -> Path:
    zip_name, onnx_name, _size = VARIANTS[variant]
    target = models_dir / onnx_name
    if target.exists() and target.stat().st_size > 1_000_000:
        print(f"✔ 识别模型已存在，跳过：{target.name}")
        return target

    print(f"  下载 {zip_name} 并解压其中的人脸识别模型 ...")
    blob = _download(f"{mirror}{INSIGHTFACE_RELEASE}/{zip_name}", f"{zip_name}（约 {VARIANTS[variant][2]}MB）")

    with zipfile.ZipFile(io.BytesIO(blob)) as zf:
        names = zf.namelist()
        print(f"  压缩包内含: {', '.join(names)}")
        if onnx_name not in names:
            raise SystemExit(f"压缩包中没有找到 {onnx_name}，请检查 variant 参数")
        (models_dir / onnx_name).write_bytes(zf.read(onnx_name))

    print(f"✔ 已保存 {target}")
    return target


def main() -> None:
    parser = argparse.ArgumentParser(description="下载人脸识别模型")
    parser.add_argument("--variant", choices=["sc", "l"], default="sc",
                        help="sc=MobileFaceNet(15MB,默认)  l=ResNet50(289MB,更准)")
    parser.add_argument("--mirror", default="", help="GitHub 加速前缀，如 https://ghfast.top/")
    parser.add_argument("--skip-detector", action="store_true")
    args = parser.parse_args()

    s = get_settings()
    s.ensure_dirs()
    models_dir = s.model_dir
    models_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 62)
    print(f" 模型目录: {models_dir}")
    print(f" 变体: {args.variant}  |  镜像: {args.mirror or '（直连 GitHub）'}")
    print("=" * 62)

    if not args.skip_detector:
        fetch_detector(models_dir, args.mirror)
    fetch_recognizer(models_dir, args.variant, args.mirror)

    print("-" * 62)
    print("当前模型目录内容：")
    for p in sorted(models_dir.glob("*.onnx")):
        print(f"  · {p.name:<40} {_human(p.stat().st_size)}")
    print("\n下一步：python scripts/selfcheck.py  # 验证引擎可加载并做人脸比对")


if __name__ == "__main__":
    main()
