#!/usr/bin/env python3
"""Small Great Expectations Core 1.21 example.

This file demonstrates the modern dataframe flow with a few expectations.
Students should extend it into a reusable Expectation Suite / Validation
Definition / Checkpoint and design actions based on severity.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

try:
    import great_expectations as gx
except ImportError as exc:  # friendlier classroom failure
    raise SystemExit("great_expectations is not installed. Run: pip install -r requirements.txt") from exc


def main() -> None:
    df = pd.read_csv(ROOT / "data" / "incoming" / "orders.csv")
    context = gx.get_context()

    # Setup Data Source and Asset
    data_source = context.data_sources.add_pandas("orders_pandas")
    asset = data_source.add_dataframe_asset(name="orders_dataframe")
    batch_definition = asset.add_batch_definition_whole_dataframe("whole_orders")
    batch = batch_definition.get_batch(batch_parameters={"dataframe": df})

    # 1. Create Expectation Suite
    suite = gx.ExpectationSuite(name="orders_suite")

    expectations = [
        gx.expectations.ExpectColumnValuesToNotBeNull(column="order_id"),
        gx.expectations.ExpectColumnValuesToBeUnique(column="order_id"),
        gx.expectations.ExpectColumnValuesToBeBetween(column="amount", min_value=0),
        gx.expectations.ExpectColumnValuesToBeInSet(column="currency", value_set=["USD", "VND"]),
    ]

    for exp in expectations:
        suite.add_expectation(exp)

    context.suites.add(suite)

    # 2. Create Validation Definition
    validation_def = gx.ValidationDefinition(
        name="orders_validation",
        data=batch_definition,
        suite=suite
    )
    context.validation_definitions.add(validation_def)

    # 3. Create Checkpoint
    checkpoint = gx.Checkpoint(
        name="orders_checkpoint",
        validation_definitions=[validation_def]
    )
    context.checkpoints.add(checkpoint)

    # Run Validation
    result = checkpoint.run(batch_parameters={"dataframe": df})

    # The result of a checkpoint is a CheckpointResult, which contains a dict of ValidationResults
    validation_result = list(result.run_results.values())[0]
    all_ok = validation_result.success

    print(f"\nGX Validation result: {'PASS' if all_ok else 'FAIL'}")
    for result in validation_result.results:
        print(f"{result.expectation_config.type:<40} success={result.success}")

    print("\nStructured GX flow complete.")


if __name__ == "__main__":
    main()
