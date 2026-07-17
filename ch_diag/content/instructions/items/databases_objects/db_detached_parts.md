# Detached parts and reasons

This instruction belongs to report item `databases_objects.db_detached_parts`.

## What this item shows
- Detached parts and reasons.
- The result is a one-shot inventory from ClickHouse system metadata.

## What to watch
- old/large/unexpected detached parts or corruption reasons

## Common fault causes
- manual detach, failed recovery/attach, or disk problem; privilege/topology scope can also make inventory incomplete

## Automatic evaluation
- Rows are inventory/advisory evidence; successful SQL execution does not assert schema or storage health.
- Cluster comparisons cover only reachable hosts in the selected cluster definition and visible objects.

## Checklist
- Validate against intended schema/topology.
- Correlate DDL, errors, replication, and storage before ALTER/ATTACH/DROP.
