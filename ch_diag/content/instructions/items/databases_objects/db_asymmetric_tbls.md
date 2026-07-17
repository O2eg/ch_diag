# Tables that are not on all nodes included in the cluster

This instruction belongs to report item `databases_objects.db_asymmetric_tbls`.

## What this item shows
- Tables that are not on all nodes included in the cluster.
- The result is a one-shot inventory from ClickHouse system metadata.

## What to watch
- objects missing where symmetry is expected

## Common fault causes
- failed DDL, restore/deploy drift, or inaccessible node; privilege/topology scope can also make inventory incomplete

## Automatic evaluation
- Rows are inventory/advisory evidence; successful SQL execution does not assert schema or storage health.
- Cluster comparisons cover only reachable hosts in the selected cluster definition and visible objects.

## Checklist
- Validate against intended schema/topology.
- Correlate DDL, errors, replication, and storage before ALTER/ATTACH/DROP.
