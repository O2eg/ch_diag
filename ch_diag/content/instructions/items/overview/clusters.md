# Configured Clusters

This instruction belongs to report item `overview.clusters`.

## What this item shows
- Cluster, shard and replica topology known to the connected node.
- This is connection and configuration context for interpreting the rest of the report.

## What to watch
- Missing/duplicate replicas, unexpected hosts/ports, shard imbalance, or transport values inconsistent with policy.

## Common fault causes
- Configuration drift, DNS changes, partial rollout, or the wrong cluster definition on this node.

## Automatic evaluation
- Rows are informational; successful collection proves the connected endpoint answered, not that its configuration is correct.
- Unexpected identity/configuration must be checked against the operator's intended target and baseline.

## Checklist
- Compare topology with the intended cluster and other nodes.
- Validate DNS/network and replica health for every discrepancy.
