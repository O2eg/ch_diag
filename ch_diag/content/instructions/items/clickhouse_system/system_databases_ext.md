# Databases common stat (based on system.tables)

This instruction belongs to report item `clickhouse_system.system_databases_ext`.

## What this item shows
- Databases common stat (based on system.tables).
- The values come from ClickHouse system tables and describe the connected node or selected cluster scope.

## What to watch
- Unexpected object/row/byte growth or strong database imbalance.

## Common fault causes
- Retention failure, ingestion change, duplicated objects, or incomplete cleanup.

## Automatic evaluation
- The table is informational and shaped by the SQL variant for the nearest preceding supported LTS.
- Visibility follows the diagnostic user's privileges; absence caused by unsupported capability is reported separately.

## Checklist
- Drill down through Top Tables and Storage Breakdown.
- Compare with filesystem capacity and retention policy.
