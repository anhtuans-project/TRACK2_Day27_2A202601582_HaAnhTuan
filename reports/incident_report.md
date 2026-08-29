# Incident Report: Mystery Incident - Massive Data Loss & Customer Corruption

## Severity
P0 (Critical)

## Summary
A catastrophic data failure occurred on 2026-08-29 characterized by massive data loss in the orders stream and corruption of the customer master data. This resulted in a CEO dashboard that showed a severe drop in order volume combined with inflated revenue for the remaining orders.

## Detection
- **Signal**: `row_count_anomaly` triggered with a score of 11.63 (MAD), indicating a massive deviation from historical norms.
- **First observed time**: 2026-08-29

## Root Cause
1. **Upstream Data Loss**: The `orders` dataset arrived with only 37 rows compared to the historical median of 252.5, indicating an upstream extraction or ingestion failure.
2. **Master Data Corruption**: The `stg_customers` table contained 6 duplicate `customer_id` entries (C0033, C0022, C0044, C0066, C0055, C0011).
3. **Transformation Logic**: `fct_daily_revenue` performs a join on `customer_id`. The presence of duplicates in the customer dimension caused a "join explosion," inflating the revenue for orders belonging to the corrupted customers.
4. **Data Staleness**: Order data arrived with a 32.9-minute delay, exceeding the 30-minute contract limit.

## Evidence
1. **Anomaly Metrics**: `reports/latest_metrics.json` showed `orders_rows: 37` vs `median=252.500`.
2. **dbt Tests**: `unique_stg_customers_customer_id` failed with 6 duplicate records.
3. **Data Exploration**: SQL queries confirmed that customers C0022, C0044, and C0011 had orders in the current batch, confirming that their revenue was doubled in the final mart.
4. **Contract Validation**: Baseline pipeline flagged a `warning` for freshness (32.9 min).

## Blast Radius
```text
src_orders (Data Loss / Staleness) 
  -> stg_orders (Volume Drop)
    -> fct_daily_revenue (Revenue Inflation via Customer Duplicates)
      -> CEO Dashboard (Critically Under-reported Volume / Inflated Revenue)
```
The CEO dashboard became completely unreliable for both volume and financial metrics.

## Mitigation
- **Immediate**: Flagged the dashboard as "Unreliable" and stopped automated reporting.
- **Data Fix**: Cleaned `stg_customers` by removing duplicate records.
- **Pipeline Fix**: Implemented a deduplication step in `stg_customers` to ensure uniqueness.
- **Upstream**: Triggered a full re-sync of the `orders` dataset to recover the missing ~215 rows.

## Recovery
- After re-syncing the source data, row counts returned to the ~250 range.
- `dbt build` was re-run; `unique_stg_customers_customer_id` passed.
- Revenue totals were cross-verified against source CSVs and found to be accurate.

## Verification
- [x] Contract healthy: Freshness returned to < 30 min.
- [x] dbt tests healthy: All staging and mart tests passing.
- [x] anomaly returned to expected range: Row count back within 3-MAD of median.
- [x] SLO healthy: Error budget burn stopped.
- [x] downstream output verified: CEO Dashboard now reflects accurate volume and revenue.

## Prevention / Action Items
| Action | Owner | Deadline | Why |
|---|---|---|---|
| Critical Volume Alert | SRE | 2026-09-01 | Immediate paging when row count drops by > 50%. |
| Hard Constraint on Customer PK | Data Eng | 2026-09-01 | Prevent any duplicate customer IDs from being loaded into the warehouse. |
| Join Guard in Marts | Analytics Eng | 2026-09-05 | Use `LEFT JOIN` with a deduplicated subquery for dimensions to prevent inflation. |
