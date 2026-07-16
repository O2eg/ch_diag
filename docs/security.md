# Security model

`ch_diag` is a read-only diagnostics collector, not an anonymizer and not a
host-hardening tool. This document defines what the collector prevents, what
it redacts, and what remains sensitive in a report.

## Execution boundary

- Vendor SQL is integrity-checked before YAML or executable content is loaded.
- SQL is restricted to one read-only `SELECT`, `WITH`, `SHOW` or `EXPLAIN`
  statement and runs with ClickHouse `readonly=2`, timeout, row and byte guards.
- Cluster names are selected from `system.clusters` and quoted by the adapter.
- Host scripts are package content, not user-supplied commands. Remote mode
  requires key authentication and a verified `known_hosts` file.
- The checksum detects corruption or replacement relative to its installed
  baseline. It cannot authenticate an attacker who can replace both Python
  code and the checksum manifest; package provenance and filesystem ownership
  remain the trust boundary.

## Secrets and metadata

Passwords should be supplied by a prompt or an environment variable named by
`password_env`. Literal TOML passwords are rejected. Passwords, private-key
contents and authentication options are not written to stdout, logs or
artifacts. CLI password arguments remain visible to local process inspection
and are therefore discouraged.

`--strip-meta` removes embedded vendor SQL/shell sources, instructions,
manifests, provenance and the HTML metadata controls. It does not redact values
collected from ClickHouse or Linux.

## Collected sensitive values

Query-log, DDL and error sources are marked `sensitive`. For query/DDL columns,
SQL string and numeric literals are replaced, common secret assignments are
redacted, NUL bytes are removed and output is bounded to 2,000 characters.
Exception/error/stack columns redact common secret assignments and are also
bounded. Other values may still contain database names, hostnames, user names,
paths, object names or business identifiers.

Treat both JSON and HTML as operationally sensitive. Outputs and run logs are
created atomically with mode `0600`; transport, retention, chat delivery and
loading into an evidence database are the operator's responsibility.

## Privileges and failure handling

A dedicated user with `SELECT ON system.*` is the baseline. The collector never
falls back to mutating SQL. Missing version capabilities are `unsupported`,
missing grants are `permission_denied`, and timeouts/errors remain explicit.
Inapplicable or unsupported items are not executed further and are omitted
from the result while their reason is visible in progress output and logs.
