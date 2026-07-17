# Keeper And ZooKeeper Event Rate

This instruction belongs to report item `snapshot_charts_clickhouse.keeper_events`.

## What this item shows
- Per-second rate of ProfileEvents whose names describe Keeper/ZooKeeper operations.
- It is coordination activity, not latency or error rate.

## What to watch
- Bursts with replication/DDL stalls or sustained activity after workload subsides.

## Common fault causes
- Replication churn, distributed DDL, reconnects, network instability, or overloaded Keeper.

## Automatic evaluation
- Absent LTS event names stay absent; high activity alone is not bad.
- Errors require dedicated error evidence.

## Checklist
- Compare replication queues/outcomes and Keeper errors.
- Inspect Keeper logs/session/network latency when activity coincides with stalls.
