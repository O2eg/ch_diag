# Replication Fetch And Send Activity

This instruction belongs to report item `snapshot_charts_clickhouse.replication_activity`.

## What this item shows
- Per-second replicated-part fetch/send activity.
- It shows transfer work, not queue length or successful completion by itself.

## What to watch
- Activity that does not reduce delay, prolonged zero progress with queued work, or replica asymmetry.

## Common fault causes
- Recovery/bootstrap, network/storage bottleneck, high inserts, unavailable replicas, or Keeper issues.

## Automatic evaluation
- Reset creates gaps; zero is healthy only with empty queues.
- Rates do not prove success.

## Checklist
- Compare queue/delay and outcomes.
- Inspect replicated_fetches, replicas, network, and disk.
