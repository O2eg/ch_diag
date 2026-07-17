# Top ClickHouse Linux Threads By CPU

This instruction belongs to report item `snapshot_charts_clickhouse.thread_cpu_top`.

## What this item shows
- Top Linux threads in /proc/PID/task ranked by interval CPU.
- TID and thread name expose the concrete worker or pool behind aggregate process CPU.

## What to watch
- One TID or named pool repeatedly dominating a saturated host.
- High CPU without matching useful throughput.

## Common fault causes
- CPU-heavy query stages, compression, merges, mutations, Keeper work, pool imbalance, or a serial bottleneck.

## Automatic evaluation
- CPU uses per-thread tick deltas; short-lived threads may be missed and Top-N membership can change.
- TID start time protects against TID reuse.

## Checklist
- Match TID/name with logged query threads.
- Compare process/host CPU, latency, merges, and pool usage.
