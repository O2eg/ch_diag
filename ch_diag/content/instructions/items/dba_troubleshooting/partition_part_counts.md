# Active Parts By Partition

This instruction belongs to report item `dba_troubleshooting.partition_part_counts`.

## What this item shows
- Active part counts/sizes per partition with an explicit advisory high-count flag.

## What to watch
- Flagged/rising partitions or many small parts relative to rows/bytes.

## Common fault causes
- Unbatched inserts, excessive partition cardinality, stalled merges, mutation/replication backlog.

## Automatic evaluation
- The threshold is a triage hint, not a ClickHouse limit or incident verdict.
- Counts are point-in-time.

## Checklist
- Check batching and PARTITION BY.
- Compare with part creation/merge rates before tuning pools.
