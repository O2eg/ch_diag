# Table engines stat (based on system.tables)

This instruction belongs to report item `databases_objects.db_tbl_engines_stat`.

## What this item shows
- Table engines stat (based on system.tables).
- The result is a one-shot inventory from ClickHouse system metadata.

## What to watch
- unexpected engines or growing engine families

## Common fault causes
- schema rollout, temporary objects, or design drift; privilege/topology scope can also make inventory incomplete

## Automatic evaluation
- Rows are inventory/advisory evidence; successful SQL execution does not assert schema or storage health.
- Cluster comparisons cover only reachable hosts in the selected cluster definition and visible objects.

## Checklist
- Validate against intended schema/topology.
- Correlate DDL, errors, replication, and storage before ALTER/ATTACH/DROP.
