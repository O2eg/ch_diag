# Config parameters (based on system.settings)

This instruction belongs to report item `clickhouse_system.system_settings`.

## What this item shows
- Config parameters (based on system.settings).
- The values come from ClickHouse system tables and describe the connected node or selected cluster scope.

## What to watch
- Risky memory, concurrency, timeout, distributed, or security settings and cross-node differences.

## Common fault causes
- Profile/user/config drift, session overrides, or emergency tuning.

## Automatic evaluation
- The table is informational and shaped by the SQL variant for the nearest preceding supported LTS.
- Visibility follows the diagnostic user's privileges; absence caused by unsupported capability is reported separately.

## Checklist
- Compare with approved defaults/baseline.
- Correlate suspect settings with the resource/error symptom they could cause.
