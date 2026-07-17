# Most Frequent Normalized Queries

This instruction belongs to report item `dba_troubleshooting.frequent_queries`.

## What this item shows
- Top normalized fingerprints from finished query_log rows with executions, latency, rows/bytes, and recency.
- normalized_query_hash is an opaque UInt64 identifier displayed exactly; it must never receive K/M/G/P scaling.

## What to watch
- High executions combined with high p95/read volume, or low-cost queries whose extreme call count creates material aggregate load.

## Common fault causes
- N+1 access, polling, retries, missing batching, or a regressed broadly used query.

## Automatic evaluation
- Bounded query_log coverage can be empty when disabled/expired.
- Older LTS SQL may compute a compatible hash; it is for correlation, not arithmetic, and collisions are theoretically possible.

## Checklist
- Copy the exact fingerprint into protected query_log investigation.
- Compare with Top CPU/Memory and workload rankings, then inspect query text/settings.
