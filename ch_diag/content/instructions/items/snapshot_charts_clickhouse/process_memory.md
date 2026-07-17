# ClickHouse Server Process Resident Memory

This instruction belongs to report item `snapshot_charts_clickhouse.process_memory`.

## What this item shows
- Resident set size (RSS) of the selected ClickHouse server PID.
- RSS includes allocator arenas and resident mappings; it is not identical to ClickHouse MemoryTracking.

## What to watch
- RSS approaching available RAM, swap/PSI pressure, or memory that keeps rising after workload subsides.
- A widening gap between RSS and MemoryTracking.

## Common fault causes
- Concurrent joins/aggregations, caches, merges, mutations, dictionaries, mapped files, allocator fragmentation, or a leak.

## Automatic evaluation
- No fixed RSS threshold is assigned because safe headroom depends on host and limits.
- A PID change yields a discontinuity.

## Checklist
- Compare RSS with MemAvailable, swap and ClickHouse MemoryTracking.
- Inspect top-memory queries and concurrency before changing limits.
