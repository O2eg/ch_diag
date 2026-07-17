# Events in cluster (based on system.events)

This instruction belongs to report item `clickhouse_system.system_events`.

## What this item shows
- Events in cluster (based on system.events).
- The values come from ClickHouse system tables and describe the connected node or selected cluster scope.

## What to watch
- Unexpected error/retry/cache/I/O counters and large differences between nodes after accounting for uptime.

## Common fault causes
- Workload volume, restart age, retries, resource pressure, or feature-specific failure.

## Automatic evaluation
- The table is informational and shaped by the SQL variant for the nearest preceding supported LTS.
- Visibility follows the diagnostic user's privileges; absence caused by unsupported capability is reported separately.

## Checklist
- Use snapshot charts for rates.
- Normalize comparisons by uptime and focus on event families matching the incident.
