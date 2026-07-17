# ClickHouse Merge Rows Per Second

This instruction belongs to report item `snapshot_charts_clickhouse.merge_row_rate`.

## What this item shows
- Rows processed per second by background MergeTree merges from cumulative merge-row events.
- It is merge work, not inserted rows or table growth.

## What to watch
- High merge work plus growing parts/replication backlog, disk saturation, or latency.
- Merge rate collapsing while parts keep accumulating.

## Common fault causes
- Many small inserted parts, undersized/blocked pools, slow disks, mutations/TTL, or backlog catch-up.

## Automatic evaluation
- Restart/reset creates a gap.
- High merge rate alone can be healthy catch-up and is not an alert.

## Checklist
- Compare with part creation, part counts, and background pools.
- Check disk latency/throughput and current merges before tuning.
