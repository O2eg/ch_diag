# Data skipping indices stat

This instruction belongs to report item `databases_objects.db_data_skipping_indices`.

## What this item shows
- Data skipping indices stat.
- The result is a one-shot inventory from ClickHouse system metadata.

## What to watch
- missing/inconsistent or filter-mismatched indexes

## Common fault causes
- partial ALTER, schema drift, or misdesigned index; privilege/topology scope can also make inventory incomplete

## Automatic evaluation
- Rows are inventory/advisory evidence; successful SQL execution does not assert schema or storage health.
- Cluster comparisons cover only reachable hosts in the selected cluster definition and visible objects.

## Checklist
- Validate against intended schema/topology.
- Correlate DDL, errors, replication, and storage before ALTER/ATTACH/DROP.
