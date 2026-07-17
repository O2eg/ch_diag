# Top Logged Query Threads By CPU

This instruction belongs to report item `snapshot_charts_clickhouse.logged_thread_cpu_top`.

## What this item shows
- Completed query threads from system.query_thread_log ranked by CPU ProfileEvents.
- Rows correlate thread_id/TID, query_id, user, and normalized identity where supported.

## What to watch
- High CPU per completed thread and the same fingerprint recurring across intervals.
- Logged query CPU aligned with host saturation.

## Common fault causes
- Expensive expressions, decompression, joins, aggregation, sorting, retries, or excessive parallelism.

## Automatic evaluation
- Only logged completed threads are covered; disabled logging, sampling, flush delay, or retention can make it empty.
- Background and current long-running work may appear only in /proc.

## Checklist
- Resolve query_id/hash in query_log.
- Compare with procfs TIDs, process CPU, and query latency.
