# Top Logged Query Threads By I/O

This instruction belongs to report item `snapshot_charts_clickhouse.logged_thread_io_top`.

## What this item shows
- Completed query threads from system.query_thread_log ranked by read/write ProfileEvents.
- It links query identity to I/O accounting recorded by ClickHouse.

## What to watch
- Large bytes per returned row, temporary-write activity, or one fingerprint repeatedly dominating.

## Common fault causes
- Full scans, weak pruning, external sort/group-by, remote reads, small-part amplification, or cache misses.

## Automatic evaluation
- Coverage depends on selected LTS columns and query-thread logging/flush/retention.
- It is logical logged attribution, not device throughput.

## Checklist
- Compare with selected parts/marks, file I/O, and disk latency.
- Inspect the exact query_id and its settings.
