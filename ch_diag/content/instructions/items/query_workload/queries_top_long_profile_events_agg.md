# Top long queries with ProfileEvents aggregated by normalized_query_hash and event_name

This instruction belongs to report item `query_workload.queries_top_long_profile_events_agg`.

## What this item shows
- Top long queries with ProfileEvents aggregated by normalized_query_hash and event_name.
- The table ranks finished query_log workload for DBA triage.

## What to watch
- High read/decompression/I/O/wait events per execution or event-mix changes for one fingerprint.

## Common fault causes
- Poor pruning, cache miss, remote I/O, heavy computation, or plan/settings regression.

## Automatic evaluation
- The ranking is bounded by query_log retention, sampling/settings, privileges, and the query LIMIT.
- normalized_query_hash values are opaque exact UInt64 identifiers for correlation and must not be scaled or treated arithmetically.

## Checklist
- Compare per-execution values, not totals alone.
- Resolve hash and correlate with parts/file/disk metrics.
