# Distribution of table engines by databases

This instruction belongs to report item `databases_objects.db_distr_tbl_engines`.

## What this item shows
- Distribution of table engines by databases.
- The result is a one-shot inventory from ClickHouse system metadata.

## What to watch
- engines inconsistent with design/replicas

## Common fault causes
- partial migration or unreviewed DDL; privilege/topology scope can also make inventory incomplete

## Automatic evaluation
- Rows are inventory/advisory evidence; successful SQL execution does not assert schema or storage health.
- Cluster comparisons cover only reachable hosts in the selected cluster definition and visible objects.

## Checklist
- Validate against intended schema/topology.
- Correlate DDL, errors, replication, and storage before ALTER/ATTACH/DROP.
