# ClickHouse Server Version

This instruction belongs to report item `overview.server`.

## What this item shows
- Server version, hostname, current database and current user.
- This is connection and configuration context for interpreting the rest of the report.

## What to watch
- Unexpected version/build, hostname, database, or user; any value that differs from the intended endpoint.

## Common fault causes
- Wrong tunnel/port, load-balancer routing, stale deployment, or credentials selecting a different account.

## Automatic evaluation
- Rows are informational; successful collection proves the connected endpoint answered, not that its configuration is correct.
- Unexpected identity/configuration must be checked against the operator's intended target and baseline.

## Checklist
- Match endpoint/version with inventory and release records.
- Use this version when interpreting selected LTS SQL and feature availability.
