# Disk Latency

This instruction belongs to report item `snapshot_charts_os.os_disk_latency`. The item is backed by `os.disk_latency` (snapshot metric).

## What this item shows
- Read and write latency by device over time.
- Storage response time during the capture window.

## What to watch
- Latency spikes on ClickHouse data, temporary, or log devices.
- Sustained high write latency during merges, mutations, or inserts.
- Read latency aligned with query slowdown.

## Common fault causes
- Slow storage.
- Queueing from high IOPS.
- Merge, mutation, insert, or fsync pressure.
- Shared storage contention.

## Automatic evaluation
- `await` is the combined average and read/write await are separate line series; they are not added.
- No fixed severity is assigned because latency targets depend on device and workload.

## Checklist
- Map devices to ClickHouse data, temporary, log, and backup paths.
- Compare with merge/file-I/O charts, current merges, and query latency.
- Investigate storage before changing query plans when latency dominates.
