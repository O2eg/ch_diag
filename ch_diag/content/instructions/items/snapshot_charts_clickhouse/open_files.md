# ClickHouse Open Files

This instruction belongs to report item `snapshot_charts_clickhouse.open_files`.

## What this item shows
- Current ClickHouse open-file gauge.
- It is not file-open operations per second.

## What to watch
- Steady growth, values near process/kernel limit, or spikes with many parts/errors.

## Common fault causes
- Many active parts, concurrent queries, dictionaries/logs, remote disks, leaks, or low nofile.

## Automatic evaluation
- No severity is assigned without effective soft/hard limits.
- Short bursts can be missed.

## Checklist
- Compare with Process Context limits.
- Inspect parts and relevant exception messages.
