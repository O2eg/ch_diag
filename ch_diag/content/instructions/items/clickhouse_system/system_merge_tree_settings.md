# MergeTree parameters (based on system.merge_tree_settings)

This instruction belongs to report item `clickhouse_system.system_merge_tree_settings`.

## What this item shows
- MergeTree parameters (based on system.merge_tree_settings).
- The values come from ClickHouse system tables and describe the connected node or selected cluster scope.

## What to watch
- Nondefault part/merge/insert/replication thresholds inconsistent across nodes or likely to mask backlog.

## Common fault causes
- Ad-hoc tuning, upgrade-default changes, or workload overrides applied too broadly.

## Automatic evaluation
- The table is informational and shaped by the SQL variant for the nearest preceding supported LTS.
- Visibility follows the diagnostic user's privileges; absence caused by unsupported capability is reported separately.

## Checklist
- Relate settings to part/merge/replication evidence.
- Change only after locating and testing the bottleneck.
