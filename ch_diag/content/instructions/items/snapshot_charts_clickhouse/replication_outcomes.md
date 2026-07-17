# Replicated Part Outcomes

This instruction belongs to report item `snapshot_charts_clickhouse.replication_outcomes`.

## What this item shows
- Rates of replicated-part success/failure/data-loss-related counters.
- It separates outcomes from transfer activity.

## What to watch
- Any repeated failed fetch/merge or data-loss increment, especially with growing delay.

## Common fault causes
- Network/replica outage, corrupt/missing part, disk error/full disk, or Keeper inconsistency.

## Automatic evaluation
- Counter deltas are reset-safe.
- Unavailable events are not fabricated as zero; severity remains conservative across LTS versions.

## Checklist
- Open replication/server errors for the same time.
- Check disk, Keeper, source replicas, and affected tables before recovery actions.
