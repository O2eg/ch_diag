# Top tables by size (with full DDL)

This instruction belongs to report item `databases_objects.db_top_tables`.

## What this item shows
- Top tables by size (with full DDL).
- The result is a one-shot inventory from ClickHouse system metadata.

## What to watch
- unexpected capacity leaders/growth or risky DDL

## Common fault causes
- retention failure, ingestion, compression, or duplication; privilege/topology scope can also make inventory incomplete

## Automatic evaluation
- Rows are inventory/advisory evidence; successful SQL execution does not assert schema or storage health.
- Cluster comparisons cover only reachable hosts in the selected cluster definition and visible objects.

## Checklist
- Validate against intended schema/topology.
- Correlate DDL, errors, replication, and storage before ALTER/ATTACH/DROP.
