# ClickHouse Configuration And Data Path Permissions

This instruction belongs to report item `clickhouse_host.config_permissions`.

## What this item shows
- Ownership and modes for the connected server configuration and conventional data/log paths, with world-writable paths marked explicitly.
- The process is selected from the database endpoint rather than from an arbitrary ClickHouse PID.

## What to watch
- World-writable paths, unexpected owners/groups, or configuration secrets readable beyond the service account.

## Common fault causes
- Manual chmod/chown, deployment mistakes, shared mounts, or inherited ACLs.

## Automatic evaluation
- This is a point-in-time host observation for the ClickHouse process selected from the connected native port.
- Container, service-manager, ACL, and custom-path context can require additional checks.

## Checklist
- Resolve active include/data/log paths.
- Correct permissions through configuration management and rotate exposed secrets.
