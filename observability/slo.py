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
    """Implements a multi-window burn-rate policy based on Google SRE standards.

    Pages on both 'Fast Burn' and 'Slow Burn' signatures to ensure critical
    budget depletion is detected regardless of the burn speed.
    """
    # Thresholds for Fast Burn (consumes budget quickly)
    FAST_BURN_THRESHOLD = 14.4
    # Thresholds for Slow Burn (consumes budget steadily)
    SLOW_BURN_THRESHOLD = 2.0

    # Fast Burn: High burn rate across both windows
    if short_window_burn >= FAST_BURN_THRESHOLD and long_window_burn >= FAST_BURN_THRESHOLD:
        return {
            "page": True,
            "severity": "critical",
            "reason": "Fast burn detected: High burn rate across both windows",
            "short_window_burn": short_window_burn,
            "long_window_burn": long_window_burn,
        }

    # Slow Burn: Moderate burn rate across both windows
    if short_window_burn >= SLOW_BURN_THRESHOLD and long_window_burn >= SLOW_BURN_THRESHOLD:
        return {
            "page": True,
            "severity": "warning",
            "reason": "Slow burn detected: Sustained moderate burn rate",
            "short_window_burn": short_window_burn,
            "long_window_burn": long_window_burn,
        }

    # Warning: One window is high, but not sustained across both
    if short_window_burn >= 6.0 or long_window_burn >= 6.0:
        return {
            "page": False,
            "severity": "warning",
            "reason": "Elevated burn rate detected in one window",
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
