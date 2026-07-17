# ClickHouse Thread And Pool Resource Usage

This instruction belongs to report item `snapshot_charts_clickhouse.thread_pool_usage`.

## What this item shows
- CPU and I/O grouped by kernel-visible ClickHouse thread names.
- This is a pool-oriented /proc view; it does not attribute shared process RSS to threads.

## What to watch
- A pool persistently dominating resources or several background pools pressured together.
- Zero I/O-access thread count when attribution was expected.

## Common fault causes
- Merge/mutation, replication, distributed-send, query, or Keeper backlog; pool sizing mismatch; slow dependencies.

## Automatic evaluation
- Grouping follows sampled thread names and can miss short-lived work.
- No pool saturation severity is guessed without effective limits.

## Checklist
- Compare names with background-task gauges and queues.
- Drill down through top TIDs and query_thread_log before changing pool sizes.
