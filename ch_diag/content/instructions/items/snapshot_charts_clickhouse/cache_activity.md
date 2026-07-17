# ClickHouse Cache Hits And Misses

This instruction belongs to report item `snapshot_charts_clickhouse.cache_activity`.

## What this item shows
- Hit and miss rates for important ClickHouse caches.
- These show interval activity, not current cache size.

## What to watch
- Misses dominating after warm-up or hit behavior degrading with latency.

## Common fault causes
- Working set over capacity, cold restart, weak locality, many small parts, disabled/undersized caches, or query-mix change.

## Automatic evaluation
- Hits/misses remain separate rates; no percentage is invented for idle intervals.
- Resets create gaps.

## Checklist
- Evaluate hits and misses together and normalize by workload.
- Compare with file I/O, disk latency, and cache settings.
