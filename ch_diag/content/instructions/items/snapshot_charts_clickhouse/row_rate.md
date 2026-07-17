# ClickHouse Row Rate

This instruction belongs to report item `snapshot_charts_clickhouse.row_rate`.

## What this item shows
- Selected-row and inserted-row rates from cumulative ClickHouse counters.
- Rows processed by the server are not the same as client result rows.

## What to watch
- Selected rows per query increasing, insert rate collapsing, or abrupt workload-mix changes.

## Common fault causes
- Weak primary-key pruning, broad scans, FINAL, high-cardinality joins, tiny insert batches, retries, or ingestion stalls.

## Automatic evaluation
- Rates are reset-safe and use actual elapsed time.
- No deployment-independent row-rate threshold exists.

## Checklist
- Normalize by query rate.
- Compare with selected bytes/parts/marks, part creation, and merges.
