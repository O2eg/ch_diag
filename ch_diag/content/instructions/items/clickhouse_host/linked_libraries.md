# ClickHouse Server Linked Libraries

This instruction belongs to report item `clickhouse_host.linked_libraries`.

## What this item shows
- One-shot ldd output for the executable of the ClickHouse server bound to the connected native port.
- The process is selected from the database endpoint rather than from an arbitrary ClickHouse PID.

## What to watch
- Libraries from unexpected or writable paths, missing dependencies, or versions outside the approved package.

## Common fault causes
- LD_LIBRARY_PATH override, manual binary replacement, package drift, or filesystem tampering.

## Automatic evaluation
- This is a point-in-time host observation for the ClickHouse process selected from the connected native port.
- Container, service-manager, ACL, and custom-path context can require additional checks.

## Checklist
- Compare paths/hashes with the package manifest.
- Investigate writable/unowned library directories before restart.
