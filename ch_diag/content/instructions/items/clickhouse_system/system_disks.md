# List of disks (based on system.disks)

This instruction belongs to report item `clickhouse_system.system_disks`.

## What this item shows
- List of disks (based on system.disks).
- The values come from ClickHouse system tables and describe the connected node or selected cluster scope.

## What to watch
- Low free space, read-only/broken disks, unexpected paths, or large capacity imbalance.

## Common fault causes
- Data growth, missing mount, permissions, or storage outage.

## Automatic evaluation
- The table is informational and shaped by the SQL variant for the nearest preceding supported LTS.
- Visibility follows the diagnostic user's privileges; absence caused by unsupported capability is reported separately.

## Checklist
- Map each ClickHouse disk to mount/device.
- Preserve merge headroom and correlate with disk errors.
