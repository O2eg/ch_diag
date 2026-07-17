# MergeTree Rows And Parts

This instruction belongs to report item `snapshot_charts_clickhouse.table_parts`.

## What this item shows
- Server-wide current MergeTree rows and active-part gauges from asynchronous metrics.
- This is trend context, not a per-table ranking.

## What to watch
- Parts growing faster than rows or persistently increasing.

## Common fault causes
- Small inserts, fine partitions, merge backlog, replication recovery, or stalled merges.

## Automatic evaluation
- Gauges may lag underlying metadata.
- No global part-count threshold is assigned.

## Checklist
- Use Partition Part Counts/Storage Breakdown to locate tables.
- Compare part creation, merge rates, disks, and pools.
