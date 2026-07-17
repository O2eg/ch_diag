# Top queries by result bytes aggregated by normalized_query_hash

This instruction belongs to report item `query_workload.queries_top_result_bytes_agg`.

## What this item shows
- Top queries by result bytes aggregated by normalized_query_hash.
- The table ranks finished query_log workload for DBA triage.

## What to watch
- A fingerprint dominating aggregate result traffic by size or frequency.

## Common fault causes
- Chatty API, repeated exports, polling, or broad result schema.

## Automatic evaluation
- The ranking is bounded by query_log retention, sampling/settings, privileges, and the query LIMIT.
- normalized_query_hash values are opaque exact UInt64 identifiers for correlation and must not be scaled or treated arithmetically.

## Checklist
- Resolve the exact hash securely.
- Compare executions, network throughput, and client behavior.
