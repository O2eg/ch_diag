# ClickHouse Current Activity

This instruction belongs to report item `snapshot_charts_clickhouse.activity`.

## What this item shows
- Point-in-time gauges for active queries, merges, mutations, and distributed sends.
- These are concurrency/backlog samples, not completion rates.

## What to watch
- Persistent concurrency, work that never drains, or distributed sends accumulating.

## Common fault causes
- Slow queries, queueing, merge/mutation debt, unavailable shards, or network/storage failure.

## Automatic evaluation
- Sampling can miss short tasks.
- Nonzero activity is not automatically unhealthy.

## Checklist
- Open Current Processes/Merges/Mutations for rows.
- Compare with latency, resources, queues, and errors.
