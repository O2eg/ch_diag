# Common queries stat by hosts

This instruction belongs to report item `query_workload.queries_by_hosts_common`.

## What this item shows
- Common queries stat by hosts.
- The table ranks finished query_log workload for DBA triage.

## What to watch
- One host handling disproportionate calls/rows/bytes or showing worse latency/errors.

## Common fault causes
- Load-balancer skew, hot shard/data, replica preference, or degraded node.

## Automatic evaluation
- The ranking is bounded by query_log retention, sampling/settings, privileges, and the query LIMIT.
- normalized_query_hash values are opaque exact UInt64 identifiers for correlation and must not be scaled or treated arithmetically.

## Checklist
- Normalize by executions and window.
- Compare topology, host resources, and identical fingerprints.
