# Top long queries

This instruction belongs to report item `query_workload.queries_top_long`.

## What this item shows
- Top long queries.
- The table ranks finished query_log workload for DBA triage.

## What to watch
- High elapsed time, large reads/memory, and repeated recent query IDs.

## Common fault causes
- Poor pruning, joins/sorts, remote waits, contention, or resource overload.

## Automatic evaluation
- The ranking is bounded by query_log retention, sampling/settings, privileges, and the query LIMIT.
- normalized_query_hash values are opaque exact UInt64 identifiers for correlation and must not be scaled or treated arithmetically.

## Checklist
- Inspect query_id/settings/plan securely.
- Compare normalized aggregate ranking and resource charts.
