# ClickHouse Memory Tracking

This instruction belongs to report item `snapshot_charts_clickhouse.memory`.

## What this item shows
- ClickHouse MemoryTracking and related current memory gauges.
- This is server allocator accounting, distinct from Linux RSS.

## What to watch
- Approaching effective limits, sharp peaks, or divergence from RSS/MemAvailable.

## Common fault causes
- Large joins/aggregations/sorts, concurrency, caches, merges, mutations, dictionaries, or fragmentation/untracked mappings.

## Automatic evaluation
- Point-in-time gauges can miss short peaks.
- No universal severity is assigned without server/user/query limits.

## Checklist
- Compare with process RSS, MemAvailable/swap, and top-memory queries.
- Inspect effective memory/overcommit settings.
