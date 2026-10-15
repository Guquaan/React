"""二维码签名工具（无状态、纯函数）。

二维码里不放明文人员 ID，而是放 `base64url(payload).hmac_sig`，
这样即使二维码被拍照传播，也无法被随意改造成别人的身份凭证。
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from typing import Any


def _b64e(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _b64d(text: str) -> bytes:
    pad = "=" * (-len(text) % 4)
    return base64.urlsafe_b64decode(text + pad)


def _sign(payload_b64: str, secret: str) -> str:
    digest = hmac.new(secret.encode("utf-8"), payload_b64.encode("ascii"), hashlib.sha256)
    return digest.hexdigest()[:32]


def issue_token(payload: dict[str, Any], secret: str) -> str:
    """生成带签名的二维码 token。"""
    payload = dict(payload)
    payload.setdefault("ts", int(time.time()))
    body = _b64e(json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8"))
    return f"{body}.{_sign(body, secret)}"


def parse_token(token: str, secret: str, *, ttl_seconds: int = 0) -> dict[str, Any]:
    """校验并解析 token，失败返回空字典（由调用方决定抛什么异常）。"""
    if not token or "." not in token:
        return {}
    body, _, sig = token.rpartition(".")
    if not body or not sig:
        return {}
    if not hmac.compare_digest(sig, _sign(body, secret)):
        return {}
    try:
        payload = json.loads(_b64d(body).decode("utf-8"))
    except Exception:  # noqa: BLE001 - 任何解码失败都视为非法 token
        return {}
    if not isinstance(payload, dict):
        return {}
    if ttl_seconds > 0:
        issued = int(payload.get("ts", 0))
        if issued <= 0 or (time.time() - issued) > ttl_seconds:
            return {}
    return payload
