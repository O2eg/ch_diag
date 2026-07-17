# New Data Parts Per Second

This instruction belongs to report item `snapshot_charts_clickhouse.part_creation_rate`.

## What this item shows
- New MergeTree data parts created per second from the selected LTS-compatible source.
- It measures parts, not inserted rows.

## What to watch
- High part rate relative to inserts or creation persistently faster than merging.

## Common fault causes
- Small batches, too many partitions, materialized views, retries, replication, or mutations.

## Automatic evaluation
- Optional logs/counters can be empty/unsupported explicitly.
- No universal part-rate threshold exists.

## Checklist
- Compare inserts, merges, and partition counts.
- Fix batching/partition design before increasing merge concurrency.
