from __future__ import annotations

from typing import Any, Iterable

import numpy as np

from observability.anomaly import zscore_detector


def approximate_token_lengths(texts: Iterable[str]) -> list[int]:
    # Deliberately simple proxy; no tokenizer/model download needed.
    return [len(str(t).split()) for t in texts]


def detect_text_length_shift(
    current_texts: Iterable[str],
    baseline_batch_means: Iterable[float],
    *,
    threshold: float = 3.0,
) -> dict[str, Any]:
    lengths = approximate_token_lengths(current_texts)
    current_mean = float(np.mean(lengths)) if lengths else 0.0
    result = zscore_detector(current_mean, baseline_batch_means, threshold=threshold)
    result["metric"] = "mean_text_length"
    result["current_mean"] = current_mean
    return result


def detect_embedding_norm_shift(
    current_norms: Iterable[float], baseline_norms: Iterable[float]
) -> dict[str, Any]:
    """Detects drift in embedding norms using robust MAD detector."""
    from observability.anomaly import mad_detector, zscore_detector

    current_mean = float(np.mean(current_norms)) if current_norms else 0.0
    baseline_list = list(baseline_norms)

    if len(baseline_list) >= 5:
        result = mad_detector(current_mean, baseline_list)
    else:
        result = zscore_detector(current_mean, baseline_list)

    result["metric"] = "embedding_norm_shift"
    result["current_mean"] = current_mean
    return result
