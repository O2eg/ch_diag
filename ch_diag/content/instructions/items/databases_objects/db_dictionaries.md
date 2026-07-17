# All dictionaries stat (based on system.dictionaries)

This instruction belongs to report item `databases_objects.db_dictionaries`.

## What this item shows
- All dictionaries stat (based on system.dictionaries).
- The result is a one-shot inventory from ClickHouse system metadata.

## What to watch
- failed/stale dictionaries, unexpected sources, or large memory

## Common fault causes
- source outage/schema drift, config, or excess size; privilege/topology scope can also make inventory incomplete

## Automatic evaluation
- Rows are inventory/advisory evidence; successful SQL execution does not assert schema or storage health.
- Cluster comparisons cover only reachable hosts in the selected cluster definition and visible objects.

## Checklist
- Validate against intended schema/topology.
- Correlate DDL, errors, replication, and storage before ALTER/ATTACH/DROP.
