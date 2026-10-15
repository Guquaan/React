"""API 冒烟测试：用 mock 引擎跑通「建人 → 注册 → 识别 → 二维码 → 记录 → 统计」整条链路。

用法：
    python scripts/smoke_api.py
（默认走 mock 引擎 + chroma 矢量库，无需下载模型即可验证接口与分层是否正确。）
"""
from __future__ import annotations

import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import cv2  # noqa: E402
import numpy as np  # noqa: E402

# 用随机色块当"假脸"，保证同一张图生成的向量稳定一致
_RNG = np.random.default_rng(7)
_img = (_RNG.integers(0, 255, (240, 240, 3), dtype=np.uint8))
_OK, _BYTES = cv2.imencode(".jpg", _img)
SAMPLE = _BYTES.tobytes()


def main() -> None:
    import time

    from fastapi.testclient import TestClient

    from app.main import app

    c = TestClient(app)
    prefix = "/api/v1"

    from app.db import init_db

    init_db()

    r = c.post(
        f"{prefix}/persons",
        json={"name": "测试用户", "department": "计算机学院", "employee_no": f"T{int(time.time())}"},
    )
    assert r.status_code == 200, r.text
    person = r.json()["data"]
    pid = person["id"]
    print(f"✔ 创建人员: {person['person_code']} ({pid})")

    r = c.post(
        f"{prefix}/faces/persons/{pid}/register",
        files={"files": ("sample.jpg", SAMPLE, "image/jpeg")},
    )
    assert r.status_code == 200, r.text
    reg = r.json()["data"]
    assert reg["accepted"] == 1, r.text
    print(f"✔ 注册人脸: 成功 {reg['accepted']} 张")

    r = c.get(f"{prefix}/persons/{pid}")
    assert r.status_code == 200 and r.json()["data"]["face_count"] == 1, r.text
    print("✔ 查询人员详情（含人脸样本）")

    r = c.post(f"{prefix}/recognition/identify", files={"file": ("probe.jpg", SAMPLE, "image/jpeg")})
    assert r.status_code == 200, r.text
    ident = r.json()["data"]
    # mock 引擎按"图像内容"生成向量，无法区分不同人；这里只验证链路与高置信度命中
    assert ident["matched"] and ident["best"]["passed"], r.text
    print(f"✔ 1:N 识别: 命中 {ident['person']['name']}，置信度 {ident['best']['confidence']:.0%}")

    r = c.get(f"{prefix}/qrcode/persons/{pid}.png")
    assert r.status_code == 200 and r.headers["content-type"] == "image/png", r.text
    print(f"✔ 生成二维码 PNG（{len(r.content)} bytes）")

    token = c.get(f"{prefix}/qrcode/persons/{pid}/payload").json()["data"]["token"]
    r = c.get(f"{prefix}/qrcode/resolve", params={"token": token})
    assert r.status_code == 200 and r.json()["data"]["valid"], r.text
    print(f"✔ 扫码解析: 获取到 {r.json()['data']['person']['name']} 的档案")

    r = c.get(f"{prefix}/recognition/logs")
    assert r.status_code == 200 and r.json()["data"]["meta"]["total"] >= 1, r.text
    print(f"✔ 识别记录: 共 {r.json()['data']['meta']['total']} 条（含时间、置信度）")

    r = c.get(f"{prefix}/stats/overview")
    assert r.status_code == 200, r.text
    ov = r.json()["data"]
    print(f"✔ 统计看板: 人员 {ov['person_count']}，识别 {ov['recognition_total']}，矢量后端 {ov['vector_backend']}")

    r = c.get(f"{prefix}/health")
    assert r.status_code == 200 and r.json()["data"]["status"] == "ok", r.text
    print("✔ 健康检查 OK")

    # 清理测试人员（连同矢量库与文件级联删除）
    c.delete(f"{prefix}/persons/{pid}")
    print("✔ 级联删除人员（清理测试数据）")

    print("\n✅ API 冒烟测试全部通过")


if __name__ == "__main__":
    main()
