# Common cluster information

This instruction belongs to report item `clickhouse_system.system_common`.

## What this item shows
- Common cluster information.
- The values come from ClickHouse system tables and describe the connected node or selected cluster scope.

## What to watch
- Node-to-node differences, unexpected build/uptime/restart, or identity inconsistent with inventory.

## Common fault causes
- Partial rollout, replacement node, wrong endpoint, or configuration drift.

## Automatic evaluation
- The table is informational and shaped by the SQL variant for the nearest preceding supported LTS.
- Visibility follows the diagnostic user's privileges; absence caused by unsupported capability is reported separately.

## Checklist
- Compare equivalent nodes and deployment records.
- Use restart time to explain counter discontinuities.
