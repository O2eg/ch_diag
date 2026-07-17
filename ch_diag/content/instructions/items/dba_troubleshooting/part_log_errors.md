# Recent Part Log Errors

This instruction belongs to report item `dba_troubleshooting.part_log_errors`.

## What this item shows
- Recent bounded error records from optional system.part_log with part operation and exception context.

## What to watch
- Repeated failures for one table/partition or merge/download errors aligned with an incident.

## Common fault causes
- Disk full/I/O, corrupt parts, permissions, failed fetch, or invalid mutation.

## Automatic evaluation
- Empty is normal with no errors, while disabled/unavailable part_log is reported separately.
- Returned errors are never downgraded by successful collection.

## Checklist
- Correlate time with server logs, replication outcomes, and disk metrics.
- Preserve evidence before detach/delete/forced recovery.
