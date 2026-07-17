# Distribution of table engines across databases and across cluster hosts

This instruction belongs to report item `databases_objects.db_distr_engines_by_hosts`.

## What this item shows
- Distribution of table engines across databases and across cluster hosts.
- The result is a one-shot inventory from ClickHouse system metadata.

## What to watch
- engine/count asymmetry on equivalent nodes

## Common fault causes
- partial DDL, migration drift, or host objects; privilege/topology scope can also make inventory incomplete

## Automatic evaluation
- Rows are inventory/advisory evidence; successful SQL execution does not assert schema or storage health.
- Cluster comparisons cover only reachable hosts in the selected cluster definition and visible objects.

## Checklist
- Validate against intended schema/topology.
- Correlate DDL, errors, replication, and storage before ALTER/ATTACH/DROP.
