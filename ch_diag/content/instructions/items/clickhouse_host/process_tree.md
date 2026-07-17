# ClickHouse Server Process Tree

This instruction belongs to report item `clickhouse_host.process_tree`.

## What this item shows
- Main ClickHouse server selected by the connected native port and its child processes.
- The process is selected from the database endpoint rather than from an arbitrary ClickHouse PID.

## What to watch
- Unexpected PID owner/executable, wrappers, extra child processes, duplicate instances, or mismatch with the DB endpoint.

## Common fault causes
- Wrong port mapping, stale/manual process, watchdog/sidecar behavior, or service compromise.

## Automatic evaluation
- This is a point-in-time host observation for the ClickHouse process selected from the connected native port.
- Container, service-manager, ACL, and custom-path context can require additional checks.

## Checklist
- Match PID/executable to service manager and Overview.
- Use the same PID when reading process/thread charts.
