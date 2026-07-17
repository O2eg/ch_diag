# ClickHouse Average Query Latency

This instruction belongs to report item `snapshot_charts_clickhouse.query_latency`.

## What this item shows
- Interval mean query latency: delta QueryTimeMicroseconds divided by delta Query.
- It is an average, not a percentile.

## What to watch
- Mean latency rising at stable rate, or spikes aligned with merges, I/O, CPU, or memory pressure.

## Common fault causes
- Slow scans/joins, resource queueing, remote shard latency, metadata contention, or a changed query mix.

## Automatic evaluation
- Intervals with no completed queries are gaps, never fake zero latency.
- Invalid/reset deltas are omitted with diagnostics.

## Checklist
- Use query_log p95/p99 for tail latency.
- Compare the exact timestamps with rate, activity, and host resources.
