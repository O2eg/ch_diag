# Report review harness

This module generates the complete reusable HTML review matrix against the
same `1 shard x 2 replicas` ClickHouse + Keeper fixture used by integration
tests. It covers every combination of:

- collection mode: `local`, SSH `remote`, `remote-db-only`;
- target scope: `node`, `cluster`;
- lifecycle: `one-shot`, `snapshots`.

One run therefore creates 12 HTML reports, their JSON artifacts and logs, plus
an `index.html` linking the whole matrix and a `review-summary.json` with item
statuses, diagnostics, sizes and browser-validation results.

Snapshot cases are full reports by default: they include the ordinary static
diagnostic sections and the snapshot charts. Keep `matrix.snapshot_tags = []`;
setting tags intentionally filters the whole report to matching items.

## Managed fixture

Prerequisites are Docker Compose, `ssh-keygen`, `ssh-keyscan`, the repository
virtual environment and an installed development package:

```bash
.venv/bin/pip install -e '.[dev]'
.venv/bin/python -m tools.report_review
```

The default [`review.toml`](review.toml):

1. generates a disposable SSH key below ignored `.test_state/report-review/`;
2. starts/reuses `tests/integration/multinode/compose.yaml` with the
   SSH-key [`compose.review.yaml`](compose.review.yaml) overlay;
3. recreates and seeds `chdiag_fixture` from the integration SQL files;
4. recreates the dedicated `chdiag_review` replicated/Distributed workload
   tables and loads the configured seed volume;
5. runs inserts, distributed scans, CPU work and occasional intentional failed
   queries throughout every snapshot case, so rate and attribution charts have
   real data;
6. generates and validates the 12-report matrix, failing it if a snapshot chart
   still has no series;
7. opens every HTML file with an installed headless Chrome/Chromium;
8. retains the fixture for fast reuse.

Set `fixture.cleanup = true` to run `docker compose down --volumes` after each
attempt. Cleanup applies only to the managed test project. The harness never
uses or changes a system-installed ClickHouse service.

Useful commands:

```bash
# Inspect the exact matrix without starting anything.
.venv/bin/python -m tools.report_review --list-cases

# Give the output a stable review name.
.venv/bin/python -m tools.report_review --run-id scheduler-review

# Treat any non-zero ch-diag collection exit as a harness failure.
.venv/bin/python -m tools.report_review --strict

# Skip Chrome/Chromium loading but keep structural HTML/JSON validation.
.venv/bin/python -m tools.report_review --skip-browser
```

The equivalent launcher is
`.venv/bin/python tools/generate_review_reports.py`.

## External fixture

For a cluster already started by integration tests or another isolated
launcher, copy [`external.example.toml`](external.example.toml), update its
native and SSH endpoints/key files, then run:

```bash
.venv/bin/python -m tools.report_review \
  --config /path/to/review-external.toml \
  --external-fixture \
  --run-id external-review
```

In external mode the harness does not start, seed through fixture SQL, stop or
remove the cluster. The example configuration also sets `workload.enabled =
false`, so it is fully read-only. If workload is explicitly enabled, only the
dedicated configured workload database is dropped/recreated and populated.
Password material is never stored in TOML: `database.password_env` names the
environment variable read by `ch-diag` and the workload client.

## Output and failure semantics

The default output is:

```text
reports/review-matrix/<run-id>/
├── index.html
├── review-summary.json
├── local/{node,cluster}/{one-shot,snapshots}/
├── remote/{node,cluster}/{one-shot,snapshots}/
└── remote-db-only/{node,cluster}/{one-shot,snapshots}/
```

Every case must produce one strict schema-v5 JSON artifact and one autonomous
HTML file with an embedded artifact. A missing/malformed artifact or browser
load failure fails the harness. With the workload enabled, a snapshot chart
without a data series or a workload that completes no cycle also fails the
harness. By default, a non-zero `ch-diag` exit is
recorded but does not abort later cases: diagnostic reports can intentionally
contain permission, timeout or unsupported statuses which are themselves
useful for review. Enable `matrix.strict_collection` or `--strict` when those
statuses must fail the whole run.

`local` always describes the collector host. With the default Docker fixture,
its OS sections therefore describe the workstation running the harness, while
SQL targets the isolated ClickHouse node. SSH `remote` is the mode whose OS
sections describe the ClickHouse container. This distinction is explicit in
the artifact `target.host_scope` field and is useful when reviewing mode
semantics.
