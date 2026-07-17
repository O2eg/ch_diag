# Local files that are in the queue to be sent to the shards (based on system.distribution_queue)

This instruction belongs to report item `activity.proc_distribution_queue`.

## What this item shows
- These local files contain new parts that are created by inserting new data into the Distributed table in asynchronous mode.
- The table shows currently active or queued work, not a historical rate.

## What to watch
- Growing files/bytes, old pending data, or repeated last_exception for one destination.

## Common fault causes
- Remote shard outage, DNS/network/auth failure, disk pressure, or distributed-table configuration.

## Automatic evaluation
- This point-in-time table can miss work that starts and finishes outside collection.
- A nonempty result is not automatically unhealthy; elapsed time, progress, backlog, and errors determine significance.

## Checklist
- Inspect oldest/error rows and remote shard health.
- Correlate with topology, network, and Errors.
