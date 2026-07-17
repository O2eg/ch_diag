# Top CPU And Memory Queries

This instruction belongs to report item `dba_troubleshooting.top_cpu_memory`.

## What this item shows
- Finished query groups ranked by aggregate CPU/memory workload without exposing query text.
- The normalized fingerprint is an exact opaque UInt64 identifier.

## What to watch
- Fingerprints dominating CPU, peak memory, or reads, especially with high p95 duration.

## Common fault causes
- Expensive joins/aggregations/sorts, poor pruning, parallelism, skew, or retries.

## Automatic evaluation
- Coverage is bounded by query_log retention/LTS capabilities.
- Ranking is diagnostic, not an automatic kill recommendation.

## Checklist
- Resolve the exact hash to query_id/text securely.
- Compare thread/process CPU, memory pressure, and selected parts.
