# ClickHouse Data Throughput

This instruction belongs to report item `snapshot_charts_clickhouse.byte_rate`.

## What this item shows
- Selected and inserted byte rates from ClickHouse event counters.
- These are logical server-processing bytes, not necessarily physical disk bytes.

## What to watch
- Read amplification, selected-byte spikes without useful output, or ingestion throughput collapse.

## Common fault causes
- Full scans, poor pruning, large columns, compression changes, bulk inserts, retries, or remote/distributed work.

## Automatic evaluation
- Reset counters create gaps.
- Logical bytes must not be interpreted as device throughput.

## Checklist
- Compare with rows, parts/marks, file I/O, network, and iostat.
- Inspect compression/query shape when bytes per row change.
