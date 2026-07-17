# Top queries by memory usage

This instruction belongs to report item `query_workload.queries_top_mem`.

## What this item shows
- Top queries by memory usage.
- The table ranks finished query_log workload for DBA triage.

## What to watch
- Queries near memory limits, repeated OOM victims, or high memory with modest output.

## Common fault causes
- Large joins/aggregations/sorts, concurrency, skew, or externalization disabled.

## Automatic evaluation
- The ranking is bounded by query_log retention, sampling/settings, privileges, and the query LIMIT.
- normalized_query_hash values are opaque exact UInt64 identifiers for correlation and must not be scaled or treated arithmetically.

## Checklist
- Inspect plan/settings and concurrent work.
- Compare MemoryTracking, RSS, and MemAvailable.
