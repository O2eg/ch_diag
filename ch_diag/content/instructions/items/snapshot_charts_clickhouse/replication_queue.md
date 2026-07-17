# Replication Queue And Delay

This instruction belongs to report item `snapshot_charts_clickhouse.replication_queue`.

## What this item shows
- Aggregate current replication queue and delay gauges from system.replicas.
- It is backlog state, not completion rate.

## What to watch
- Queue/delay growing over consecutive samples, read-only replicas, or backlog without transfer progress.

## Common fault causes
- Network/storage/Keeper trouble, unavailable source, merge pressure, or a failing task.

## Automatic evaluation
- Short transient backlog can be normal.
- Aggregation can hide one bad table, so drill-down is required.

## Checklist
- Use Replication Summary/Queue for table rows.
- Correlate with activity/outcomes, Keeper, disk, and network.
