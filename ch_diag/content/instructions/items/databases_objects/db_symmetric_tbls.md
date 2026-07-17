# Tables that are on all nodes included in the cluster

This instruction belongs to report item `databases_objects.db_symmetric_tbls`.

## What this item shows
- Tables that are on all nodes included in the cluster.
- The result is a one-shot inventory from ClickHouse system metadata.

## What to watch
- unexpected absence or same name with different DDL

## Common fault causes
- comparison scope, privilege, or incomplete topology; privilege/topology scope can also make inventory incomplete

## Automatic evaluation
- Rows are inventory/advisory evidence; successful SQL execution does not assert schema or storage health.
- Cluster comparisons cover only reachable hosts in the selected cluster definition and visible objects.

## Checklist
- Validate against intended schema/topology.
- Correlate DDL, errors, replication, and storage before ALTER/ATTACH/DROP.
