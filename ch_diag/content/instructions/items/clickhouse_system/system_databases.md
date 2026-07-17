# List of databases (based on system.databases)

This instruction belongs to report item `clickhouse_system.system_databases`.

## What this item shows
- List of databases (based on system.databases).
- The values come from ClickHouse system tables and describe the connected node or selected cluster scope.

## What to watch
- Unexpected/missing databases, engines, or metadata paths.

## Common fault causes
- Incomplete restore/deploy, access scope, or replicated-database drift.

## Automatic evaluation
- The table is informational and shaped by the SQL variant for the nearest preceding supported LTS.
- Visibility follows the diagnostic user's privileges; absence caused by unsupported capability is reported separately.

## Checklist
- Compare with inventory and other nodes.
- Resolve missing databases before table-asymmetry conclusions.
