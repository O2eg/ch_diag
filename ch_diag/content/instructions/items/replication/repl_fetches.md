# Currently running background fetches (based on system.replicated_fetches)

This instruction belongs to report item `replication.repl_fetches`.

## What this item shows
- Currently running background fetches (based on system.replicated_fetches).
- The table exposes ReplicatedMergeTree state coordinated through Keeper or ZooKeeper.

## What to watch
- Long/slow fetches, repeated source/part, or concurrent transfers saturating network/disk.

## Common fault causes
- Slow source replica, network loss/throttling, disk contention, or recovery bootstrap.

## Automatic evaluation
- The item is point-in-time evidence; a short transient queue/fetch can be normal, while persistence across captures is significant.
- Local scope describes this node's view and must not be presented as cluster-wide certainty.

## Checklist
- Check elapsed/bytes/rate/source.
- Compare queue delay, network, and disk charts.
