# Changed Settings

This instruction belongs to report item `overview.changed_settings`.

## What this item shows
- Settings which differ from their profile defaults.
- This is connection and configuration context for interpreting the rest of the report.

## What to watch
- Changes to memory, concurrency, timeouts, distributed behavior, inserts, joins, or readonly/security controls.

## Common fault causes
- Profile/user/session overrides, rollout drift, or emergency tuning left in place.

## Automatic evaluation
- Rows are informational; successful collection proves the connected endpoint answered, not that its configuration is correct.
- Unexpected identity/configuration must be checked against the operator's intended target and baseline.

## Checklist
- Compare each setting with the approved baseline and incident timeline.
- Confirm server/profile/user/session scope before reverting.
