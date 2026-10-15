"""相似度评分与判定规则（纯函数，业务核心可单测）。

准确率保障策略（对应需求 3）：
  1. **精确余弦相似度**：ArcFace 特征已 L2 归一化，点积即余弦；
  2. **可配置工作点**：默认 cos >= 0.40 才算命中，低于则判定"未识别"而不是硬猜，
     避免误报拉低准确率；
  3. **置信度线性映射** (cos+1)/2，使 cos=0.40 ↔ confidence=0.70，
     配置里的两个阈值天然对齐，不会出现"相似度过了但置信度没过"的矛盾；
  4. 多张注册样本取最优匹配（max pooling），显著提升同人召回率。
"""
from __future__ import annotations

import numpy as np

# 映射区间：余弦 [-1, 1] -> 置信度 [0, 1]
_COS_MIN = -1.0
_COS_MAX = 1.0


def to_confidence(cosine: float) -> float:
    """余弦相似度 -> 归一化置信度 [0, 1]。

    cos = 0.40 -> 0.70   （与默认 FACE_CONFIDENCE_FLOOR 一致）
    cos = 1.00 -> 1.00   （完全相同的人脸特征）
    cos = 0.00 -> 0.50   （完全无关）
    """
    v = (float(cosine) - _COS_MIN) / (_COS_MAX - _COS_MIN)
    return float(np.clip(v, 0.0, 1.0))


def confidence_to_cosine(confidence: float) -> float:
    """反向换算：给定最低置信度要求，得到对应的余弦阈值。"""
    return float(np.clip(confidence, 0.0, 1.0)) * (_COS_MAX - _COS_MIN) + _COS_MIN


def is_match(cosine: float, threshold: float) -> bool:
    """是否判定为同一个人。"""
    return float(cosine) >= float(threshold)


def should_accept_registration(
    *,
    quality_score: float,
    face_width: int,
    face_height: int,
    min_size: int,
    min_quality: float = 0.35,
) -> tuple[bool, str]:
    """注册前的质量闸门 —— 脏样本是准确率的最大杀手。

    返回 (是否接受, 原因)。
    """
    if min(face_width, face_height) < min_size:
        return False, f"人脸过小（{face_width}x{face_height}，要求最短边 ≥ {min_size}px），请靠近镜头重拍"
    if quality_score < min_quality:
        return False, f"人脸质量偏低（{quality_score:.2f} < {min_quality:.2f}），可能模糊或侧脸，请重拍"
    return True, ""


def rank_candidates(raw: list[tuple[str, float]]) -> list[tuple[str, float]]:
    """按相似度降序排序，供 1:N 返回 TopK。"""
    return sorted(raw, key=lambda x: x[1], reverse=True)
