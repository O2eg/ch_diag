# List of macros (based on system.macros)

This instruction belongs to report item `clickhouse_system.system_macros`.

## What this item shows
- Contains full output of system.macros.
- The values come from ClickHouse system tables and describe the connected node or selected cluster scope.

## What to watch
- Missing or duplicate shard/replica macros, or values inconsistent with Keeper paths.

## Common fault causes
- Copied configuration, wrong host identity, or rollout drift.

## Automatic evaluation
- The table is informational and shaped by the SQL variant for the nearest preceding supported LTS.
- Visibility follows the diagnostic user's privileges; absence caused by unsupported capability is reported separately.

## Checklist
- Compare macros with system.replicas paths.
- Ensure replica macro uniqueness before ON CLUSTER/replicated DDL.
