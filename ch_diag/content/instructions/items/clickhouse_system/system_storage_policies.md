# List of storage policies (based on system.storage_policies)

This instruction belongs to report item `clickhouse_system.system_storage_policies`.

## What this item shows
- List of storage policies (based on system.storage_policies).
- The values come from ClickHouse system tables and describe the connected node or selected cluster scope.

## What to watch
- Missing disks/volumes, unexpected priority/move_factor, or node-to-node differences.

## Common fault causes
- Configuration drift, mount changes, or partial storage migration.

## Automatic evaluation
- The table is informational and shaped by the SQL variant for the nearest preceding supported LTS.
- Visibility follows the diagnostic user's privileges; absence caused by unsupported capability is reported separately.

## Checklist
- Cross-check system.disks and OS mounts.
- Verify free space and consistency before moving data.
