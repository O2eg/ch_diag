# ClickHouse File I/O Throughput

This instruction belongs to report item `snapshot_charts_clickhouse.file_io`.

## What this item shows
- Read/write rates from ClickHouse file-descriptor ProfileEvents.
- Operations can be served by page cache, so this is not a physical-device meter.

## What to watch
- Spikes aligned with latency, disk saturation, or merge pressure.
- Large divergence from /proc/device metrics.

## Common fault causes
- Scans, merges, mutations, inserts, temp files, logs, cache misses, or many small parts.

## Automatic evaluation
- Counter resets create gaps; idle valid intervals can be zero.
- No physical I/O claim is made.

## Checklist
- Compare with process I/O and iostat.
- Correlate writes with merges/parts and reads with selected bytes.
