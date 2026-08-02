# ch_diag machine orchestration contract

The normal CLI is intended for operators. Automation can use the versioned
`ch_play/component/v1` machine transport without parsing progress lines or
human-readable errors.

Machine options precede the command:

```bash
ch-diag --machine --component-capabilities

ch-diag --machine --request-id plan-001 explain-plan \
  --ch-version 25.8 --run-mode one-shot \
  --collection-mode remote-db-only --target-scope node

ch-diag --machine --request-id collect-001 one-shot \
  --host clickhouse.example.net --user ch_diag \
  --collection-mode remote-db-only --target-scope node \
  --output-format json --out-dir reports/node

ch-diag --machine --request-id inspect-001 \
  validate-artifact reports/node/report.json

ch-diag --machine --request-id summary-001 \
  summarize reports/node/report.json
```

`--component-capabilities` reports `ch_play/capabilities/v1`, supported commands,
schema versions, collection modes, target scopes, secret policy and machine
exit codes. Capability discovery does not connect to ClickHouse.

Every machine command emits one JSON object with:

- component and contract versions;
- command and caller-supplied request ID;
- `succeeded`, `partial`, `failed` or `cancelled` status;
- deterministic result data;
- output artifact path, SHA-256 and size when a file exists;
- redacted warnings and a structured error.

`explain-plan` returns a deterministic plan summary and hashes the full resolved
plan. `summarize` and `validate-artifact` validate schema-v5 input before
reporting counts or hashes. A report summary includes collection statuses,
completeness, fallback triggers, degraded state, diagnostics and snapshot count;
it does not interpret findings or recommend remediation.

Machine exit codes are stable:

| Code | Meaning |
|---:|---|
| `0` | Success |
| `2` | Validation error |
| `3` | Precondition failed |
| `4` | Unsupported operation |
| `5` | Partial collection with retained artifacts |
| `6` | Execution error |
| `7` | Cancelled |
| `8` | Artifact ownership error |

Normal mode retains its existing `0`, `1`, `2` and `130` conventions. Machine
mode never promotes a partial collection to success merely because a JSON or
HTML file exists.
