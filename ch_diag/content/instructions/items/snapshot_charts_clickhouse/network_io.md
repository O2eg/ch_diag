# ClickHouse Network Throughput

This instruction belongs to report item `snapshot_charts_clickhouse.network_io`.

## What this item shows
- ClickHouse network send/receive byte rates from server counters.
- It aggregates client, distributed-query, and replication traffic visible to those events.

## What to watch
- Unexpected spikes/asymmetry or high traffic with falling query throughput.

## Common fault causes
- Distributed queries, large results, replication, remote disks, retries, or inefficient cross-shard work.

## Automatic evaluation
- Counter resets create gaps.
- The chart does not identify peer, protocol, retransmit, or packet loss.

## Checklist
- Compare with OS interfaces/packets and replication activity.
- Inspect distributed queries and query_log in the same interval.
