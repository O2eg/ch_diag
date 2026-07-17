# ClickHouse Server Process CPU

This instruction belongs to report item `snapshot_charts_clickhouse.process_cpu`.

## What this item shows
- CPU consumed by the selected ClickHouse server PID in each interval.
- Process CPU comes from /proc counter deltas; 100% means one fully occupied logical CPU, so a multithreaded server can exceed 100%.

## What to watch
- Sustained use near total host CPU capacity.
- Spikes aligned with higher query latency, merge backlog, or one dominant thread.

## Common fault causes
- Large scans, joins, aggregation, decompression, or expression evaluation.
- Background merges/mutations or colocated workload competing for CPU.

## Automatic evaluation
- No universal CPU severity is assigned.
- PID restart or invalid counter decrease creates a gap, not a negative rate.

## Checklist
- Compare with host CPU utilization/load.
- Use top Linux threads and query_thread_log to identify the responsible query or background pool.
