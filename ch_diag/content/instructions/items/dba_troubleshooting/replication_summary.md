# Replication Health Summary

This instruction belongs to report item `dba_troubleshooting.replication_summary`.

## What this item shows
- Local replicated-table queue, delay, session/read-only, and active-replica state.

## What to watch
- Growing queue/delay, read-only/session-expired state, lost/inactive replicas.

## Common fault causes
- Keeper/network outage, disk pressure, unavailable source, failing task, or merge backlog.

## Automatic evaluation
- Thresholds are advisory and node scope does not claim cluster-wide health.
- Transient backlog differs from persistent lag.

## Checklist
- Inspect the worst table in replication_queue/replicas.
- Correlate Keeper/errors, outcomes, disk, and network.
