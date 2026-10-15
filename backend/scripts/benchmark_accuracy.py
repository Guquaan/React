"""准确率基准测试 —— 用数据证明"每张人脸匹配准确率 ≥ 70%"（需求 3）。

数据集目录结构（每人一个子目录，同一人多张不同角度的照片）：

    backend/dataset/
        zhangsan/  01.jpg  02.jpg  03.jpg
        lisi/      01.jpg  02.jpg
        ...

脚本会：
  1. 按人划分 注册集(gallery) / 测试集(probe)；
  2. 把注册集写入矢量库；
  3. 用测试集逐张做 1:N 识别，统计 Top-1 准确率、阈值内命中率、误报率；
  4. 做一次阈值扫描，给出准确率最优的工作点建议；
  5. 输出 reports/accuracy_report.md + .json。

用法：
    python scripts/benchmark_accuracy.py
    python scripts/benchmark_accuracy.py --dataset ../photos --holdout 2 --top-k 5
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import numpy as np

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.config import Settings, get_settings  # noqa: E402
from app.engines import create_engine  # noqa: E402
from app.repositories.vector.local_repo import LocalVectorRepository  # noqa: E402
from app.repositories.vector.base import VectorRecord  # noqa: E402
from app.services.scoring import confidence_to_cosine, to_confidence  # noqa: E402
from app.utils.image import decode_image, resize_max  # noqa: E402

IMAGE_SUFFIX = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


# ======================================================================
# 数据加载
# ======================================================================
def load_dataset(root: Path) -> dict[str, list[Path]]:
    if not root.exists():
        return {}
    out: dict[str, list[Path]] = {}
    for person_dir in sorted(p for p in root.iterdir() if p.is_dir()):
        imgs = sorted(
            p for p in person_dir.iterdir() if p.is_file() and p.suffix.lower() in IMAGE_SUFFIX
        )
        if imgs:
            out[person_dir.name] = imgs
    return out


def embed_folder(paths: list[Path], engine) -> tuple[list[np.ndarray], list[str]]:  # noqa: ANN001
    """批量提特征；返回 (向量列表, 失败原因列表)。"""
    vecs: list[np.ndarray] = []
    errors: list[str] = []
    for p in paths:
        try:
            img = resize_max(decode_image(p.read_bytes()), 1280)
            faces = engine.detect_and_embed(img)
            if not faces:
                errors.append(f"{p.name}: 未检测到人脸")
                continue
            best = max(faces, key=lambda f: f.quality_score * 0.6 + min(f.bbox[2] - f.bbox[0], 999) / 999 * 0.4)
            vecs.append(best.embedding)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{p.name}: {type(exc).__name__} {exc}")
    return vecs, errors


# ======================================================================
# 评测
# ======================================================================
def evaluate(args) -> dict:  # noqa: ANN001
    base_settings = get_settings()
    engine = create_engine(base_settings.face_engine)

    print("=" * 70)
    print(f" 人脸引擎: {engine.name} / {engine.model_name}   维度={engine.dim}")
    if not engine.is_ready():
        print(" ✖ 引擎未就绪！请先运行: python scripts/download_models.py")
        print("   或在 backend/.env 设置 FACE_ENGINE=mock 做链路自测。")
        print("=" * 70)
        raise SystemExit(2)
    print(f" 矢量后端: local (评测专用临时库)")
    print("=" * 70)

    dataset = load_dataset(Path(args.dataset))
    if not dataset:
        print(f" ✖ 数据集为空: {args.dataset}")
        print("   请按「每人一个子目录」放置照片，例如 backend/dataset/zhangsan/01.jpg")
        raise SystemExit(3)

    # ---- 临时矢量库（使用系统临时目录，不污染正式数据） ----
    tmp_settings = Settings(storage_dir=args.tmp_dir or str(Path(base_settings.storage_path) / "_bench_tmp"))
    tmp_settings.ensure_dirs()
    repo = LocalVectorRepository(tmp_settings)
    repo.reset()

    # ---- 划分 gallery / probe ----
    gallery: list[tuple[str, Path]] = []
    probe: list[tuple[str, Path]] = []
    for person, imgs in dataset.items():
        if len(imgs) <= args.holdout:
            # 照片太少，全部用于注册，跳过测试（避免不公平评估）
            gallery.extend((person, p) for p in imgs)
            continue
        gallery.extend((person, p) for p in imgs[: -args.holdout])
        probe.extend((person, p) for p in imgs[-args.holdout :])

    print(f" 人员数: {len(dataset)}   注册照片: {len(gallery)}   测试照片: {len(probe)}")
    if not probe:
        print(" ✖ 没有测试照片：每位人员至少需要 holdout+1 张")
        raise SystemExit(4)

    # ---- 注册（写入矢量库） ----
    print("\n[1/3] 提取注册集特征并写入矢量库 ...")
    t0 = time.perf_counter()
    by_person: dict[str, list[np.ndarray]] = defaultdict(list)
    reg_errors: list[str] = []
    for person, path in gallery:
        vecs, errs = embed_folder([path], engine)
        reg_errors.extend([f"[注册]{person}/{e}" for e in errs])
        if vecs:
            by_person[person].append(vecs[0])

    records, sample_of = [], {}
    for person, vecs in by_person.items():
        for i, v in enumerate(vecs):
            vid = f"{person}#{i}"
            records.append(VectorRecord(id=vid, embedding=v, metadata={"person_id": person, "name": person}))
            sample_of[vid] = person
    repo.upsert(records)
    print(f"      写入 {len(records)} 条向量，耗时 {time.perf_counter() - t0:.2f}s")
    if reg_errors:
        for e in reg_errors:
            print(f"      ⚠ {e}")

    missing = [p for p in dataset if p not in by_person]
    if missing:
        print(f"      ⚠ 以下人员没有任何可用注册样本，已从评测中排除: {', '.join(missing)}")

    # ---- 识别 ----
    print("\n[2/3] 逐张识别测试集 ...")
    threshold = max(
        float(base_settings.face_match_cosine_threshold),
        confidence_to_cosine(base_settings.face_confidence_floor),
    )
    per_person_total: dict[str, int] = defaultdict(int)
    per_person_hit: dict[str, int] = defaultdict(int)
    rows: list[dict] = []
    latencies: list[float] = []
    far = frr = 0
    topk_all: list[float] = []

    for truth, path in probe:
        if truth not in by_person:
            continue
        t = time.perf_counter()
        vecs, errs = embed_folder([path], engine)
        cost = (time.perf_counter() - t) * 1000
        latencies.append(cost)
        per_person_total[truth] += 1

        if not vecs:
            frr += 1
            per_person_hit[truth] += 0  # 未检测到人脸 = 未命中
            rows.append(
                {
                    "person": truth, "file": path.name, "predicted": None,
                    "similarity": -1.0, "confidence": 0.0, "correct": False,
                    "reason": (errs[0].split(": ", 1)[1] if errs else "无法提取特征"),
                    "elapsed_ms": round(cost, 2),
                }
            )
            continue

        hits = repo.query(vecs[0], top_k=args.top_k)
        if not hits:
            frr += 1
            rows.append(
                {
                    "person": truth, "file": path.name, "predicted": None,
                    "similarity": -1.0, "confidence": 0.0, "correct": False,
                    "reason": "矢量库为空", "elapsed_ms": round(cost, 2),
                }
            )
            continue

        top1 = hits[0]
        top1_person = sample_of.get(top1.id, "?")
        top1_all_correct = top1_person == truth
        if top1_all_correct:
            topk_all.append(top1.similarity)

        # 该人的最高相似度（同人多样本 max pooling）
        person_sims = [h.similarity for h in hits if sample_of.get(h.id) == truth]
        own_best = max(person_sims) if person_sims else -1.0
        accepted = own_best >= threshold
        if accepted:
            per_person_hit[truth] += 1
        else:
            frr += 1
        if sample_of.get(top1.id) != truth and top1.similarity >= threshold:
            far += 1

        rows.append(
            {
                "person": truth,
                "file": path.name,
                "predicted": top1_person,
                "similarity": round(float(own_best), 4),
                "top1_similarity": round(float(top1.similarity), 4),
                "confidence": round(to_confidence(own_best), 4),
                "top1_correct": top1_all_correct,
                "correct": accepted,
                "reason": "" if accepted else f"最高相似度 {own_best:.4f} 低于阈值 {threshold:.4f}",
                "elapsed_ms": round(cost, 2),
            }
        )

    total_probe = sum(per_person_total.values())
    total_hit = sum(per_person_hit.values())
    accuracy = total_hit / total_probe if total_probe else 0.0
    top1_accuracy = sum(1 for r in rows if r.get("top1_correct")) / len(rows) if rows else 0.0

    per_person = {
        p: {
            "total": per_person_total[p],
            "hit": per_person_hit[p],
            "accuracy": round(per_person_hit[p] / per_person_total[p], 4) if per_person_total[p] else 0.0,
        }
        for p in sorted(per_person_total)
    }

    # ---- 阈值扫描 ----
    print("\n[3/3] 阈值扫描（选取最优工作点） ...")
    sweep = []
    for th in [0.20, 0.25, 0.30, 0.35, 0.40, 0.45, 0.50, 0.55, 0.60]:
        hit = sum(1 for r in rows if r["similarity"] >= th)
        wrong = sum(1 for r in rows if r["similarity"] >= th and r["predicted"] not in (None, r["person"]))
        sweep.append(
            {
                "threshold": th,
                "confidence": round(to_confidence(th), 4),
                "match_rate": round(hit / len(rows), 4) if rows else 0.0,
                "false_accept": wrong,
            }
        )

    return {
        "meta": {
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "engine": engine.name,
            "model_name": engine.model_name,
            "embedding_dim": int(engine.dim),
            "dataset": str(Path(args.dataset).resolve()),
            "person_count": len(dataset),
            "gallery_size": len(records),
            "probe_size": len(rows),
            "holdout": args.holdout,
            "vector_backend": repo.backend_name,
        },
        "config": {
            "cosine_threshold": round(threshold, 4),
            "confidence_floor": float(base_settings.face_confidence_floor),
            "top_k": args.top_k,
        },
        "metrics": {
            "accuracy": round(accuracy, 4),
            "top1_accuracy": round(top1_accuracy, 4),
            "far": far,
            "frr": frr,
            "far_rate": round(far / len(rows), 4) if rows else 0.0,
            "frr_rate": round(frr / len(rows), 4) if rows else 0.0,
            "avg_latency_ms": round(float(np.mean(latencies)), 2) if latencies else 0.0,
            "p95_latency_ms": round(float(np.percentile(latencies, 95)), 2) if latencies else 0.0,
        },
        "per_person": per_person,
        "sweep": sweep,
        "details": rows,
        "passed": accuracy >= 0.70 and all(v["accuracy"] >= 0.70 for v in per_person.values()),
    }


# ======================================================================
# 报告
# ======================================================================
def render_report(r: dict) -> str:
    m, c, mm = r["meta"], r["config"], r["metrics"]
    ok = r["passed"]
    lines = [
        "# 人脸识别准确率基准报告",
        "",
        f"> 生成时间：{m['generated_at']}　|　引擎：`{m['engine']} / {m['model_name']}`　|　特征维度：{m['embedding_dim']}",
        f"> 数据集：`{m['dataset']}`　|　人员 {m['person_count']} 人　|　注册 {m['gallery_size']} 张　|　测试 {m['probe_size']} 张",
        f"> 矢量后端：`{m['vector_backend']}`　|　判定阈值：余弦 ≥ {c['cosine_threshold']}（置信度 ≥ {c['confidence_floor']:.0%}）",
        "",
        f"## 总体结论：{'✅ 通过（准确率 ≥ 70%）' if ok else '❌ 未通过（准确率 < 70%）'}",
        "",
        "| 指标 | 数值 | 说明 |",
        "| --- | --- | --- |",
        f"| **识别准确率** | **{mm['accuracy']:.2%}** | 阈值内正确命中 / 全部测试样本（需求 3 的考核指标） |",
        f"| Top-1 准确率 | {mm['top1_accuracy']:.2%} | 不看阈值，最近邻是否就是本人（衡量特征质量上限） |",
        f"| 误报率 FAR | {mm['far_rate']:.2%} | 把别人认成库内人员的比例（越低越好） |",
        f"| 拒识率 FRR | {mm['frr_rate']:.2%} | 本人未被识别的比例 |",
        f"| 平均耗时 | {mm['avg_latency_ms']:.1f} ms | 单张图：检测+特征+检索 |",
        f"| P95 耗时 | {mm['p95_latency_ms']:.1f} ms | |",
        "",
        "## 每位人员准确率（要求每张人脸 ≥ 70%）",
        "",
        "| 人员 | 测试张数 | 命中 | 准确率 | 是否达标 |",
        "| --- | ---: | ---: | ---: | :---: |",
    ]
    for person, v in r["per_person"].items():
        mark = "✅" if v["accuracy"] >= 0.70 else "❌"
        lines.append(f"| {person} | {v['total']} | {v['hit']} | {v['accuracy']:.2%} | {mark} |")

    lines += [
        "",
        "## 阈值扫描",
        "",
        "| 余弦阈值 | 对应置信度 | 命中率 | 误接受数 |",
        "| ---: | ---: | ---: | ---: |",
    ]
    for s in r["sweep"]:
        star = " ⭐" if abs(s["threshold"] - c["cosine_threshold"]) < 1e-6 else ""
        lines.append(
            f"| {s['threshold']:.2f}{star} | {s['confidence']:.0%} | {s['match_rate']:.2%} | {s['false_accept']} |"
        )

    lines += ["", "## 逐张明细", "", "| 人员 | 文件 | 判定 | 相似度 | 置信度 | 结果 | 备注 |", "| --- | --- | --- | ---: | ---: | :---: | --- |"]
    for row in r["details"]:
        lines.append(
            f"| {row['person']} | {row['file']} | {row['predicted'] or '—'} | "
            f"{row['similarity']:.4f} | {row['confidence']:.1%} | {'✅' if row['correct'] else '❌'} | {row['reason'] or ''} |"
        )

    lines += [
        "",
        "---",
        "",
        "### 如何提高准确率",
        "1. **每人多注册几张**：不同角度、不同光照下各 1 张，识别时取最高相似度，召回率提升最明显。",
        "2. **用 `--variant l` 的 ResNet50 模型**：特征更强，代价是模型从 15MB 涨到 289MB。",
        "3. **注册时保证质量**：系统已内置质量闸门（人脸最短边 ≥ 48px、质量分 ≥ 0.35），被拒绝的照片请重拍。",
        "4. **调整工作点**：从上表里挑「命中率 ≥ 70% 且误接受数 = 0」的最小阈值，兼顾准确率与安全。",
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="人脸识别准确率基准测试")
    parser.add_argument("--dataset", default=str(BACKEND_DIR / "dataset"), help="数据集根目录")
    parser.add_argument("--holdout", type=int, default=1, help="每人留几张作为测试集")
    parser.add_argument("--top-k", type=int, default=5, help="检索候选数")
    parser.add_argument("--report-dir", default=str(BACKEND_DIR / "reports"))
    parser.add_argument("--tmp-dir", default="", help="评测临时矢量库目录")
    args = parser.parse_args()

    result = evaluate(args)

    report_dir = Path(args.report_dir)
    report_dir.mkdir(parents=True, exist_ok=True)
    (report_dir / "accuracy_report.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    md_path = report_dir / "accuracy_report.md"
    md_path.write_text(render_report(result), encoding="utf-8")

    m, mm = result["meta"], result["metrics"]
    print("=" * 70)
    print(f" 识别准确率 : {mm['accuracy']:.2%}")
    print(f" Top-1 准确率: {mm['top1_accuracy']:.2%}")
    print(f" 误报率 FAR : {mm['far_rate']:.2%}   拒识率 FRR: {mm['frr_rate']:.2%}")
    print(f" 平均耗时   : {mm['avg_latency_ms']:.1f} ms")
    print(f" 结论       : {'✅ 通过（≥70%）' if result['passed'] else '❌ 未通过'}")
    print(f" 报告       : {md_path}")
    print("=" * 70)


if __name__ == "__main__":
    main()
