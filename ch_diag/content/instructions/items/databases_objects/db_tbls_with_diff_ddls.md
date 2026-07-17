# Tables with the same name, but with different DDLs

This instruction belongs to report item `databases_objects.db_tbls_with_diff_ddls`.

## What this item shows
- Tables with the same name, but with different DDLs.
- The result is a one-shot inventory from ClickHouse system metadata.

## What to watch
- engine/key/partition/TTL/codec/settings differences

## Common fault causes
- partial DDL, manual change, or serialization/version difference; privilege/topology scope can also make inventory incomplete

## Automatic evaluation
- Rows are inventory/advisory evidence; successful SQL execution does not assert schema or storage health.
- Cluster comparisons cover only reachable hosts in the selected cluster definition and visible objects.

## Checklist
- Validate against intended schema/topology.
- Correlate DDL, errors, replication, and storage before ALTER/ATTACH/DROP.
