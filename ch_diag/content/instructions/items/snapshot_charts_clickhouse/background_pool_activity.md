# ClickHouse Background Pool Tasks

This instruction belongs to report item `snapshot_charts_clickhouse.background_pool_activity`.

## What this item shows
- Current active task counts for available ClickHouse background pools.
- These are sampled gauges, not completed-task rates.

## What to watch
- A pool persistently at capacity, several saturated together, or zero activity while its queue grows.

## Common fault causes
- Merge/replication backlog, slow storage/network, oversized tasks, pool mismatch, or a stuck dependency.

## Automatic evaluation
- Names vary by LTS and missing declared capabilities are explicit.
- No saturation severity is guessed without limits.

## Checklist
- Compare with pool-size settings and queue lengths.
- Inspect merges, mutations, replication, and distributed queue.
