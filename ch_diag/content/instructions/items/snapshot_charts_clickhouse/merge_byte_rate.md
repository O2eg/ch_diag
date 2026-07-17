# ClickHouse Merge Throughput

This instruction belongs to report item `snapshot_charts_clickhouse.merge_byte_rate`.

## What this item shows
- Logical byte throughput processed by MergeTree merges.
- It must not be equated directly with physical disk throughput.

## What to watch
- Sustained merge work saturating storage or falling near zero while part backlog grows.

## Common fault causes
- Ingestion/small parts, TTL/codecs, mutations, catch-up, slow disks, or pool contention.

## Automatic evaluation
- Rates are reset-safe and use real elapsed time.
- Compression/cache make logical and device bytes differ.

## Checklist
- Compare merge rows/bytes with disk I/O, pools, and parts.
- Inspect current merge progress/ETA.
