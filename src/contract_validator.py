"""Simple contract validator used as the starter baseline.

The implementation intentionally covers only common deterministic checks.
Students are expected to extend it with:
- stronger type validation/coercion rules,
- freshness checks,
- cross-field/cross-table assertions,
- severity-aware actions (block/quarantine/warn),
- richer observability metadata.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
import yaml


def _issue(
    check: str,
    *,
    column: str | None,
    severity: str,
    passed: bool,
    details: str,
) -> dict[str, Any]:
    return {
        "check": check,
        "column": column,
        "severity": severity,
        "passed": bool(passed),
        "details": details,
    }


def load_contract(path: str | Path) -> dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def validate_dataframe(df: pd.DataFrame, contract: dict[str, Any]) -> tuple[list[dict[str, Any]], pd.Series]:
    issues: list[dict[str, Any]] = []
    failed_mask = pd.Series(False, index=df.index)
    columns = contract.get("columns", {})

    for column, rules in columns.items():
        severity = rules.get("severity", "warning")
        required = bool(rules.get("required", False))
        is_critical = (severity == "critical")

        if column not in df.columns:
            if required:
                issues.append(
                    _issue(
                        "required_column",
                        column=column,
                        severity=severity,
                        passed=False,
                        details=f"Missing required column: {column}",
                    )
                )
                if is_critical:
                    failed_mask[:] = True
            continue

        series = df[column]

        if required:
            null_mask = series.isna()
            null_count = int(null_mask.sum())
            issues.append(
                _issue(
                    "not_null",
                    column=column,
                    severity=severity,
                    passed=(null_count == 0),
                    details=f"null_count={null_count}",
                )
            )
            if is_critical:
                failed_mask |= null_mask

        if rules.get("unique"):
            duplicate_mask = series.duplicated(keep=False)
            duplicate_count = int(duplicate_mask.sum())
            issues.append(
                _issue(
                    "unique",
                    column=column,
                    severity=severity,
                    passed=(duplicate_count == 0),
                    details=f"duplicate_rows={duplicate_count}",
                )
            )
            if is_critical:
                failed_mask |= duplicate_mask

        accepted = rules.get("accepted_values")
        if accepted is not None:
            invalid_mask = series.notna() & ~series.isin(accepted)
            invalid_count = int(invalid_mask.sum())
            issues.append(
                _issue(
                    "accepted_values",
                    column=column,
                    severity=severity,
                    passed=(invalid_count == 0),
                    details=f"invalid_count={invalid_count}; accepted={accepted}",
                )
            )
            if is_critical:
                failed_mask |= invalid_mask

        # Type validation
        type_rule = rules.get("type")
        if type_rule:
            series_not_null = series.notna()
            drift_mask = pd.Series(False, index=series.index)
            if type_rule in ("number", "integer"):
                converted = pd.to_numeric(series, errors="coerce")
                drift_mask = series_not_null & converted.isna()
                if type_rule == "integer":
                    float_mask = converted.notna() & (converted % 1 != 0)
                    drift_mask |= float_mask
            elif type_rule == "datetime":
                converted = pd.to_datetime(series, errors="coerce")
                drift_mask = series_not_null & converted.isna()

            drift_count = int(drift_mask.sum())
            issues.append(
                _issue(
                    "type_drift",
                    column=column,
                    severity=severity,
                    passed=(drift_count == 0),
                    details=f"type_drift_count={drift_count}; expected={type_rule}",
                )
            )
            if is_critical:
                failed_mask |= drift_mask

        # Starter numeric range support.
        if "min" in rules or "max" in rules:
            numeric = pd.to_numeric(series, errors="coerce")
            invalid = pd.Series(False, index=series.index)
            if "min" in rules:
                invalid |= numeric < rules["min"]
            if "max" in rules:
                invalid |= numeric > rules["max"]
            invalid_count = int(invalid.fillna(False).sum())
            issues.append(
                _issue(
                    "range",
                    column=column,
                    severity=severity,
                    passed=(invalid_count == 0),
                    details=f"invalid_count={invalid_count}",
                )
            )
            if is_critical:
                failed_mask |= invalid.fillna(False)

    # Freshness validation
    freshness_rules = contract.get("freshness")
    if freshness_rules:
        freshness_col = freshness_rules.get("column")
        max_delay = freshness_rules.get("max_delay_minutes")
        f_severity = freshness_rules.get("severity", "warning")

        if freshness_col and max_delay and freshness_col in df.columns:
            latest_date = pd.to_datetime(df[freshness_col].max(), errors="coerce")
            if pd.isna(latest_date):
                issues.append(
                    _issue(
                        "freshness",
                        column=freshness_col,
                        severity=f_severity,
                        passed=False,
                        details="Could not determine latest date for freshness check",
                    )
                )
                if f_severity == "critical":
                    failed_mask[:] = True
            else:
                delay = (pd.Timestamp.now(tz='UTC') - latest_date.tz_localize('UTC') if latest_date.tzinfo is None else pd.Timestamp.now(tz='UTC') - latest_date).total_seconds() / 60
                issues.append(
                    _issue(
                        "freshness",
                        column=freshness_col,
                        severity=f_severity,
                        passed=(delay <= max_delay),
                        details=f"delay_minutes={delay:.2f}; max_delay={max_delay}",
                    )
                )
                if f_severity == "critical" and delay > max_delay:
                    failed_mask[:] = True

    return issues, failed_mask


def failed_issues(issues: list[dict[str, Any]], min_severity: str | None = None) -> list[dict[str, Any]]:
    failed = [i for i in issues if not i.get("passed", False)]
    if min_severity is None:
        return failed
    order = {"info": 0, "warning": 1, "critical": 2}
    threshold = order[min_severity]
    return [i for i in failed if order.get(i.get("severity", "warning"), 1) >= threshold]


def determine_action(issues: list[dict[str, Any]]) -> str:
    """Determines the pipeline action based on the severity of failed issues.

    Mapping:
    - critical -> block
    - warning -> quarantine
    - info -> warn
    - no issues -> allow
    """
    failed = failed_issues(issues)
    if not failed:
        return "allow"

    # Priority: block > quarantine > warn
    severity_map = {"critical": "block", "warning": "quarantine", "info": "warn"}
    priority = {"block": 3, "quarantine": 2, "warn": 1, "allow": 0}

    highest_action = "allow"
    for issue in failed:
        severity = issue.get("severity", "warning")
        action = severity_map.get(severity, "warn")
        if priority[action] > priority[highest_action]:
            highest_action = action

    return highest_action

