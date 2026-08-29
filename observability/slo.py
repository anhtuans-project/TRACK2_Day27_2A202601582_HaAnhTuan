from __future__ import annotations

from typing import Any


def calculate_slo(target: float, bad_events: int, total_events: int) -> dict[str, Any]:
    if not 0 < target < 1:
        raise ValueError("target must be between 0 and 1 (exclusive)")
    if bad_events < 0 or total_events < 0 or bad_events > total_events:
        raise ValueError("invalid event counts")
    allowed_bad_rate = 1.0 - target
    if total_events == 0:
        return {
            "target": target,
            "actual_bad_rate": 0.0,
            "allowed_bad_rate": allowed_bad_rate,
            "burn_rate": 0.0,
            "remaining_error_budget_fraction": 1.0,
            "breached": False,
        }
    actual_bad_rate = bad_events / total_events
    burn_rate = actual_bad_rate / allowed_bad_rate
    consumed_fraction = min(1.0, actual_bad_rate / allowed_bad_rate)
    return {
        "target": target,
        "actual_bad_rate": actual_bad_rate,
        "allowed_bad_rate": allowed_bad_rate,
        "burn_rate": burn_rate,
        "remaining_error_budget_fraction": max(0.0, 1.0 - consumed_fraction),
        "breached": bool(actual_bad_rate > allowed_bad_rate),
    }


def evaluate_multiwindow_burn(
    *,
    short_window_burn: float,
    long_window_burn: float,
    policy: str = "starter",
) -> dict[str, Any]:
    """Implements a multi-window burn-rate policy to distinguish sustained burn from spikes.

    A critical page is triggered only if both short and long windows show high burn,
    reducing noise from transient spikes.
    """
    # Industry standard thresholds for SRE burn rates
    CRITICAL_THRESHOLD = 14.4
    WARNING_THRESHOLD = 6.0

    # Critical: Sustained fast burn (both windows high)
    if short_window_burn >= CRITICAL_THRESHOLD and long_window_burn >= CRITICAL_THRESHOLD:
        return {
            "page": True,
            "severity": "critical",
            "reason": "Sustained fast burn detected across both windows",
            "short_window_burn": short_window_burn,
            "long_window_burn": long_window_burn,
        }

    # Warning: Either window is high, or they are both moderately high
    if short_window_burn >= WARNING_THRESHOLD or long_window_burn >= WARNING_THRESHOLD:
        return {
            "page": False,
            "severity": "warning",
            "reason": "Burn rate elevation detected; monitoring for sustainability",
            "short_window_burn": short_window_burn,
            "long_window_burn": long_window_burn,
        }

    return {
        "page": False,
        "severity": "info",
        "reason": "Burn rates within normal range",
        "short_window_burn": short_window_burn,
        "long_window_burn": long_window_burn,
    }
