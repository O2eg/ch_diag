# Replication queue (based on system.replication_queue)

This instruction belongs to report item `replication.repl_queue`.

## What this item shows
- Tasks from replication queues stored in Clickhouse Keeper or ZooKeeper, for tables in the ReplicatedMergeTree family.
- The table exposes ReplicatedMergeTree state coordinated through Keeper or ZooKeeper.

## What to watch
- Old/retrying tasks, GET_PART/MERGE_PARTS backlog, or repeated exception.

## Common fault causes
- Unavailable source, Keeper/network trouble, disk pressure, corrupt part, or slow merges.

## Automatic evaluation
- The item is point-in-time evidence; a short transient queue/fetch can be normal, while persistence across captures is significant.
- Local scope describes this node's view and must not be presented as cluster-wide certainty.

## Checklist
- Find the oldest/failing task and table.
- Correlate replicas, fetches, outcomes, and logs.
