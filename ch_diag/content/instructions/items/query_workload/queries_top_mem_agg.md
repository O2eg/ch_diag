# Top queries by memory usage aggregated by normalized_query_hash

This instruction belongs to report item `query_workload.queries_top_mem_agg`.

## What this item shows
- Top queries by memory usage aggregated by normalized_query_hash.
- The table ranks finished query_log workload for DBA triage.

## What to watch
- Fingerprints with high peak/average memory and enough calls for concurrency risk.

## Common fault causes
- Memory-heavy shape, data skew, excessive parallelism, or retry duplication.

## Automatic evaluation
- The ranking is bounded by query_log retention, sampling/settings, privileges, and the query LIMIT.
- normalized_query_hash values are opaque exact UInt64 identifiers for correlation and must not be scaled or treated arithmetically.

## Checklist
- Resolve fingerprint and inspect concurrent copies.
- Compare aggregate contribution with server/OS memory.
