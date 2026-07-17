# Status of replicated tables (based on system.replicas)

This instruction belongs to report item `replication.repl_tables`.

## What this item shows
- Status of replicated tables (based on system.replicas).
- The table exposes ReplicatedMergeTree state coordinated through Keeper or ZooKeeper.

## What to watch
- Read-only/session-expired replicas, growing delay/queue, lost parts, or inactive replicas.

## Common fault causes
- Keeper outage, disk/network failure, unavailable replicas, or a stuck queue task.

## Automatic evaluation
- The item is point-in-time evidence; a short transient queue/fetch can be normal, while persistence across captures is significant.
- Local scope describes this node's view and must not be presented as cluster-wide certainty.

## Checklist
- Start with the worst table and last exception.
- Cross-check queue/fetches, Keeper, and storage.
