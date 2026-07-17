# Top ClickHouse Linux Threads By I/O

This instruction belongs to report item `snapshot_charts_clickhouse.thread_io_top`.

## What this item shows
- Top ClickHouse Linux threads by per-thread /proc I/O rates.
- It identifies TID and kernel thread name for sampled work.

## What to watch
- One TID/pool repeatedly dominating reads or writes.
- High thread I/O aligned with device latency, or procfs permission diagnostics.

## Common fault causes
- Merge/mutation workers, scans, inserts, fetches, log writers, small parts, or cache misses.

## Automatic evaluation
- Rates use only stable successful observations; disappeared/reset threads create gaps.
- Kernel permissions and short-lived threads limit completeness.

## Checklist
- Correlate TID with query_thread_log and thread CPU.
- Compare sums with process I/O and physical device metrics.
