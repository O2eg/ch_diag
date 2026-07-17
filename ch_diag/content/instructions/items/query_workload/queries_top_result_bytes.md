# Top queries by result bytes

This instruction belongs to report item `query_workload.queries_top_result_bytes`.

## What this item shows
- Top queries by result bytes.
- The table ranks finished query_log workload for DBA triage.

## What to watch
- Large individual results or result bytes disproportionate to useful work.

## Common fault causes
- Unbounded SELECT/export, missing LIMIT/aggregation, or inefficient API payload.

## Automatic evaluation
- The ranking is bounded by query_log retention, sampling/settings, privileges, and the query LIMIT.
- normalized_query_hash values are opaque exact UInt64 identifiers for correlation and must not be scaled or treated arithmetically.

## Checklist
- Check consumer intent and network/client pressure.
- Inspect exact query_id and apply semantic result limits.
