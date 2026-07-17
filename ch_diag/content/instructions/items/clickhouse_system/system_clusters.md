# List of clusters

This instruction belongs to report item `clickhouse_system.system_clusters`.

## What this item shows
- Contains full output of system.clusters.
- The values come from ClickHouse system tables and describe the connected node or selected cluster scope.

## What to watch
- Replica error fields, unexpected addresses/ports, shard imbalance, or different topology across nodes.

## Common fault causes
- DNS/network problems, stale cluster configuration, or incomplete rollout.

## Automatic evaluation
- The table is informational and shaped by the SQL variant for the nearest preceding supported LTS.
- Visibility follows the diagnostic user's privileges; absence caused by unsupported capability is reported separately.

## Checklist
- Compare with replication/distributed-queue errors.
- Validate the definition on every node.
