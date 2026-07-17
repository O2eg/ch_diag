# ClickHouse Server Process I/O

This instruction belongs to report item `snapshot_charts_clickhouse.process_io`.

## What this item shows
- Read/write byte rates from /proc/PID/io for the selected ClickHouse server.
- This kernel process accounting is independent from ClickHouse ProfileEvents and device iostat.

## What to watch
- Throughput saturating the backing device, or sustained I/O while useful query throughput falls.
- Permission/PID diagnostics instead of values.

## Common fault causes
- Wide scans, merges/mutations, inserts, temporary files, backups, cache misses, or excessive small parts.

## Automatic evaluation
- Rates use actual elapsed time; reset counters create gaps.
- Access failure is never converted into zero I/O.

## Checklist
- Compare with iostat throughput/utilization/latency.
- Use top thread I/O and ClickHouse file I/O to separate process, thread, logical, and physical views.
