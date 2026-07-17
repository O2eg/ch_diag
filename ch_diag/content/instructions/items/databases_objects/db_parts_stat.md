# Dataparts statistics

This instruction belongs to report item `databases_objects.db_parts_stat`.

## What this item shows
- Dataparts statistics.
- The result is a one-shot inventory from ClickHouse system metadata.

## What to watch
- many small parts or abnormal row/size distribution

## Common fault causes
- small inserts, fine partitions, stalled merges, or recovery; privilege/topology scope can also make inventory incomplete

## Automatic evaluation
- Rows are inventory/advisory evidence; successful SQL execution does not assert schema or storage health.
- Cluster comparisons cover only reachable hosts in the selected cluster definition and visible objects.

## Checklist
- Validate against intended schema/topology.
- Correlate DDL, errors, replication, and storage before ALTER/ATTACH/DROP.
