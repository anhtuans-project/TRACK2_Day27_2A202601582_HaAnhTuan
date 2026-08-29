# AI Agent Decision Log

## Decision 1: Contract Validation & Quarantine (Phase 1)
- **Hypothesis**: Basic validation isn't enough; we need a way to block bad data without stopping the entire pipeline for non-critical errors.
- **Prompt / request to agent**: "Implement a quarantine mechanism for critical failures in the contract validator."
- **Agent proposal**: Modify `validate_dataframe` to return a `failed_mask` for critical errors, then use this mask in `run_baseline.py` to split the dataframe into `clean_df` and `quarantine_df`.
- **Evidence/test**: Injected duplicate PKs; verified that duplicate rows landed in `data/quarantine/orders_quarantine.csv` while the pipeline continued with clean data.
- **Accept / reject / revise**: Accept.
- **Why**: Allows for high availability of the pipeline while maintaining data integrity.

## Decision 2: dbt Transformation Protection (Phase 2)
- **Hypothesis**: The revenue inflation is caused by a join explosion (many-to-one) in the mart.
- **Prompt / request to agent**: "Create a dbt unit test to detect revenue inflation caused by duplicate active customer records."
- **Agent proposal**: Create a mock dataset in `unit_tests.yml` with one order linked to two "active" customer records, then assert that the resulting revenue is not double-counted.
- **Evidence/test**: The unit test failed on the original logic and passed after the join logic was corrected/constrained.
- **Accept / reject / revise**: Accept.
- **Why**: Proves the bug exists in a reproducible way without needing real production data.

## Decision 3: Anomaly Detection Method (Phase 3)
- **Hypothesis**: Z-score is too sensitive to outliers in historical data.
- **Prompt / request to agent**: "Improve `auto` mode in `detect_anomaly` to be more robust."
- **Agent proposal**: Implement a hybrid approach that prefers Median Absolute Deviation (MAD) when sufficient history ($\ge 5$ points) is available, falling back to Z-score otherwise.
- **Evidence/test**: Tested against a dataset with a single massive historical spike; MAD correctly ignored the spike, whereas Z-score shifted the mean and missed the current anomaly.
- **Accept / reject / revise**: Accept.
- **Why**: MAD is a more robust measure of central tendency and dispersion for noisy data.

## Decision 4: SLO Alerting Policy (Phase 5)
- **Hypothesis**: Simple burn rate alerts cause too many "false positive" pages during transient spikes.
- **Prompt / request to agent**: "Implement a multi-window burn-rate policy to distinguish sustained burn from spikes."
- **Agent proposal**: Only trigger a `critical` page if *both* the short-window and long-window burn rates exceed the critical threshold (14.4). Use a warning threshold (6.0) for single-window spikes.
- **Evidence/test**: Verified with test cases where a 1-hour spike triggers a warning but not a page, while a 6-hour sustained failure triggers a page.
- **Accept / reject / revise**: Accept.
- **Why**: Aligns with SRE best practices to reduce alert fatigue and prioritize sustained outages.

## Decision 5: Mystery Incident Investigation (Phase 6)
- **Hypothesis**: The massive drop in row count is a data loss incident, and the revenue inflation is a recurrence of the customer duplication issue.
- **Prompt / request to agent**: "Investigate the mystery incident using all observability tools."
- **Agent proposal**: 1) Run baseline to check row count and freshness. 2) Run GX to check row validity. 3) Run dbt tests to find corruption. 4) Use SQL to confirm the revenue inflation.
- **Evidence/test**:
    - Baseline: 37 rows vs 252 median (Score 11.63).
    - dbt: `unique_stg_customers_customer_id` failed (6 duplicates).
    - SQL: Confirmed 3 customers with orders were duplicated, doubling their revenue.
- **Accept / reject / revise**: Accept.
- **Why**: Comprehensive evidence from multiple layers of the pipeline confirmed both data loss and data corruption.
