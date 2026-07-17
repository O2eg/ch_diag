# MergeTree Stored Bytes

This instruction belongs to report item `snapshot_charts_clickhouse.table_bytes`.

## What this item shows
- Server-wide stored MergeTree bytes from asynchronous metrics.
- It is capacity trend context, not exact filesystem inventory.

## What to watch
- Unexpected growth, divergence from rows, or approach to filesystem capacity.

## Common fault causes
- Ingestion, weaker compression, retention gaps, mutation/detached data, or temporary merge space.

## Automatic evaluation
- Gauge freshness/scope follow asynchronous metrics.
- Filesystem free space is authoritative for exhaustion.

## Checklist
- Compare Disk Usage, Storage Breakdown, and compression.
- Check TTL/retention and merge headroom.
