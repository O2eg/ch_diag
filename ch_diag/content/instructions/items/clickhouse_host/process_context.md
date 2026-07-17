# ClickHouse Process Limits And Security Context

This instruction belongs to report item `clickhouse_host.process_context`.

## What this item shows
- Command, executable, resource limits and kernel security state for the selected ClickHouse server.
- The process is selected from the database endpoint rather than from an arbitrary ClickHouse PID.

## What to watch
- Low nofile/nproc limits, unexpected arguments, deleted executable, or weak/unexpected security confinement.

## Common fault causes
- Service-unit drift, manual startup, incomplete hardening, or incorrect limits.

## Automatic evaluation
- This is a point-in-time host observation for the ClickHouse process selected from the connected native port.
- Container, service-manager, ACL, and custom-path context can require additional checks.

## Checklist
- Compare limits with open files/connections and deployment policy.
- Verify systemd/container configuration and executable ownership.
