# Top long queries aggregated by normalized_query_hash

This instruction belongs to report item `query_workload.queries_top_long_agg`.

## What this item shows
- Top long queries aggregated by normalized_query_hash.
- The table ranks finished query_log workload for DBA triage.

## What to watch
- Fingerprints with high p95/max and many executions, not only one outlier.

## Common fault causes
- Regressed query shape, changed data distribution, retries, or missing pruning.

## Automatic evaluation
- The ranking is bounded by query_log retention, sampling/settings, privileges, and the query LIMIT.
- normalized_query_hash values are opaque exact UInt64 identifiers for correlation and must not be scaled or treated arithmetically.

## Checklist
- Copy the exact hash into query_log.
- Compare calls, p95, reads, and total contribution.
