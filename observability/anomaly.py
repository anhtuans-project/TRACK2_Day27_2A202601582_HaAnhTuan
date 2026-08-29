"""Anomaly detection starter.

Z-score is deliberately the default baseline. Students should improve `auto`
mode for seasonality/outliers rather than deleting the simple implementation.
"""
from __future__ import annotations

from typing import Any, Iterable

import numpy as np


def zscore_detector(current: float, history: Iterable[float], threshold: float = 3.0) -> dict[str, Any]:
    values = np.asarray(list(history), dtype=float)
    if values.size < 3:
        return {"is_anomaly": False, "score": 0.0, "method": "zscore", "reason": "insufficient_history"}
    mean = float(np.mean(values))
    std = float(np.std(values))
    if std == 0:
        score = float("inf") if float(current) != mean else 0.0
    else:
        score = abs(float(current) - mean) / std
    return {
        "is_anomaly": bool(score > threshold),
        "score": float(score),
        "method": "zscore",
        "reason": f"mean={mean:.3f}, std={std:.3f}, threshold={threshold}",
    }


def mad_detector(current: float, history: Iterable[float], threshold: float = 3.5) -> dict[str, Any]:
    """Robust example, intentionally incomplete around zero-MAD edge cases."""
    values = np.asarray(list(history), dtype=float)
    if values.size < 5:
        return {"is_anomaly": False, "score": 0.0, "method": "mad", "reason": "insufficient_history"}
    median = float(np.median(values))
    mad = float(np.median(np.abs(values - median)))
    if mad == 0:
        score = 0.0 if float(current) == median else float("inf")
        reason = f"median={median:.3f}, mad=0.0, threshold={threshold}"
    else:
        score = 0.6745 * abs(float(current) - median) / mad
        reason = f"median={median:.3f}, mad={mad:.3f}, threshold={threshold}"

    return {
        "is_anomaly": bool(score > threshold),
        "score": float(score),
        "method": "mad",
        "reason": reason,
    }


def detect_anomaly(
    current: float,
    history: Iterable[float],
    *,
    method: str = "auto",
    threshold: float = 3.0,
    context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Stable lab API.

    Improved `auto` mode:
    - Uses `same_segment_history` from context if available (e.g. for seasonality).
    - Adjusts threshold if a `known_event` is present to reduce false positives.
    - Prefers MAD for robustness if enough data is present.
    """
    # 1. Resolve history based on context (Seasonality/Segments)
    effective_history = history
    if context and "same_segment_history" in context:
        effective_history = context["same_segment_history"]

    # 2. Adjust threshold based on context (Known Events)
    effective_threshold = threshold
    if context and context.get("known_event"):
        # Be more lenient during known events
        effective_threshold *= 1.5

    # 3. Dispatch to detector
    if method == "mad":
        return mad_detector(current, effective_history, threshold=effective_threshold)

    if method in {"zscore", "auto"}:
        if method == "auto":
            # Use MAD if we have enough data for robustness
            hist_list = list(effective_history)
            if len(hist_list) >= 5:
                result = mad_detector(current, hist_list, threshold=effective_threshold)
                result["method"] = "auto:mad"
                return result

        # Fallback to Z-score
        result = zscore_detector(current, effective_history, threshold=effective_threshold)
        if method == "auto":
            result["method"] = "auto:zscore"
        return result

    raise ValueError(f"Unsupported method: {method}")
