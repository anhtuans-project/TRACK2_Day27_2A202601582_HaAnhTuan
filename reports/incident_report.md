# Incident Report: Revenue Inflation in CEO Dashboard

## Severity
P1 (Critical)

## Summary
A combination of source data quality degradation (duplicate records and type drift in `orders`) and a transformation logic bug in the revenue mart led to significant revenue inflation in the CEO dashboard. The lack of automated guards allowed these errors to propagate from source to the final report.

## Detection
- **Signal**: Anomaly detection on `daily_revenue` triggered a high Z-score/MAD alert.
- **First observed time**: 2026-08-27

## Root Cause
1. **Source Layer**: The `orders` source dataset experienced "type drift" and contained duplicate `order_id` entries, violating the data contract.
2. **Transformation Layer**: In `fct_daily_revenue`, a join between `stg_orders` and `stg_customers` produced a many-to-one relationship because of duplicate active customer records. This caused the `sum(amount)` to inflate, effectively double-counting revenue for affected orders.

## Evidence
1. **GX Validation**: Great Expectations checkpoints identified critical violations of the `orders` contract (nulls in non-nullable columns and PK duplicates).
2. **dbt Unit Tests**: A specifically designed unit test mocked a many-to-one customer-order relationship, proving that the existing SQL logic inflated revenue.
3. **Anomaly Metrics**: The `mad_detector` flagged the revenue spike as a significant outlier compared to the 30-day historical median.

## Blast Radius
The failure propagated as follows:
```text
src_orders (Duplicates/Drift) 
  -> stg_orders (Contract Breach)
    -> fct_daily_revenue (Revenue Inflation)
      -> CEO Dashboard (Incorrect Financials)
```
The primary impacted column was `daily_revenue`, which directly affected the CEO's view of company performance.

## Mitigation
- **Data Quarantine**: Implemented a circuit-breaker in `src/contract_validator.py` that splits data into `clean_df` and `quarantine_df` based on critical contract failures.
- **Transformation Guards**: Added `unique` and `not_null` tests to `stg_orders` and `fct_daily_revenue` using dbt.
- **Unit Testing**: Integrated dbt unit tests to verify transformation logic against edge cases (like duplicate customers) before deployment.

## Recovery
- The pipeline was updated to quarantine bad source data.
- `fct_daily_revenue` was recalculated using only the cleaned dataset.
- Revenue totals were verified against raw source logs and confirmed to be accurate.

## Verification
- [x] Contract healthy: GX checkpoints passing for `orders` source.
- [x] dbt tests healthy: `dbt test` returns no failures across staging and marts.
- [x] anomaly returned to expected range: Revenue metrics now within 3-MAD of historical median.
- [x] SLO healthy / budget understood: Burn rate is currently $< 1.0$ (no budget being consumed).
- [x] downstream output verified: CEO Dashboard totals match verified aggregates.

## Prevention / Action Items
| Action | Owner | Deadline | Why |
|---|---|---|---|
| Implement Source-Side Contracts | Data Eng | 2026-09-10 | Prevent bad data from even entering the pipeline. |
| Mandatory Unit Tests for Marts | Analytics Eng | 2026-09-15 | Ensure financial logic is robust against duplicates. |
| Multi-Window SLO Alerting | SRE | 2026-09-01 | Distinguish transient spikes from sustained burns to reduce alert fatigue. |
