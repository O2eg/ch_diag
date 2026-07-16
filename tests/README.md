# Tests

The test suite covers the generic schema-v5 engine, ClickHouse adapter,
declarative content, Linux probes, autonomous renderer, packaging, supported
Python versions, real ClickHouse SQL and a two-replica Keeper cluster.

## Layout

- `unit/` — no Docker or network: artifact, content/planner, version selection,
  adapter concurrency, samplers, shell syntax, secure output, configuration,
  legacy wrapper and fixture contracts.
- `browser/` — self-contained HTML behavior in headless Chromium.
- `integration/test_live_clickhouse.py` — every applicable SQL source, TLS,
  privileges, SSH host scripts and one-shot/snapshots lifecycle in all three
  connection modes.
- `integration/docker/` — reusable single-node ClickHouse image with native
  TLS, SSH, `lshw`, `iostat` and other host tools.
- `integration/test_multinode_clickhouse.py` — real node/cluster queries and
  reports against two replicas and ClickHouse Keeper.
- `integration/multinode/` — custom reusable ClickHouse image, matching Keeper,
  topology configuration and deterministic multi-engine fixture data.
- `tools/run_legacy_clickhouse_matrix.py` — pinned ClickHouse `20.3–22.2`
  boundary images on native amd64 runners.

## Default checks

Install development dependencies and run the checks used by the normal CI
Python job:

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[dev]'

python -m compileall -q ch_diag tools tests
ruff check ch_diag tests tools
python tools/normalize_sql_outputs.py --check
ch-diag validate
pytest -q
python -m build
```

Without live endpoint environment variables, the integration modules skip
cleanly. Run a narrow module or test while developing:

```bash
pytest -q tests/unit/test_samplers.py
pytest -q tests/unit/test_content_and_planner.py::test_vendor_content_loads_and_covers_legacy_inventory
```

The main unit groups are:

- `test_artifact_and_renderer.py` — schema-v5 values, metadata stripping and
  autonomous HTML payload.
- `test_clickhouse_adapter.py` — bounded worker concurrency, cleanup and
  timeout behavior.
- `test_config_and_legacy_cli.py` — TOML/env/CLI precedence and old-command
  translation.
- `test_content_and_planner.py` — manifests, integrity, upstream OS lock,
  filters and version/scope planning.
- `test_legacy_matrix.py` — pinned images, architecture selection, reusable
  legacy runner behavior and current SQL normalizer contracts.
- `test_multinode_fixture.py` — custom compose topology and fixture contracts.
- `test_samplers.py` — legacy/current `iostat`, procfs, process metrics and
  chart budgets.
- `test_secure_output.py` — mode-`0600` atomic output and symlink replacement.
- `test_shell_sources.py` — POSIX syntax for every packaged shell source.
- `test_versioning.py` — numeric parsing and half-open variant ranges.

## Minimum Python and clean wheel

CI runs the default checks on Python 3.10, 3.11, 3.12 and 3.13. To run the
default suite under the minimum interpreter without installing it on the host:

```bash
docker run --rm --init \
  --volume "$PWD:/workspace:ro" \
  --workdir /workspace \
  --env PYTHONDONTWRITEBYTECODE=1 \
  python:3.10-slim-bookworm \
  sh -ec 'python -m pip install --quiet ".[dev]"; python -m pytest -q -p no:cacheprovider'
```

Package verification must install only the built wheel, from outside the
source tree, then validate that bundled content is present:

```bash
python -m build

docker run --rm \
  --volume "$PWD:/src:ro" \
  --workdir /tmp \
  python:3.10-slim-bookworm \
  sh -ec '
    python -m pip install /src/dist/ch_diag-*.whl
    ch-diag validate
    ch-diag item-id-list >/tmp/items.tsv
    test -s /tmp/items.tsv
  '
```

## Browser renderer

Install the optional browser extra and Chromium:

```bash
python -m pip install -e '.[test,browser]'
python -m playwright install chromium
pytest -q -m browser tests/browser
```

The tests open reports through `file://`, reject page/console errors, exercise
table filtering, SQL/instruction/metadata dialogs, theme switching, zoom and
drag-pan, and verify SVG, PNG and CSV downloads. They also prove that
`--strip-meta` removes source payload and controls.

## Single-node live ClickHouse

The complete reusable setup and environment are documented in
[`integration/docker/README.md`](integration/docker/README.md). With every
documented TLS/SSH variable present, run:

```bash
pytest -q -m integration tests/integration/test_live_clickhouse.py
```

This is an execution smoke suite, not a value-by-value golden report. Every
applicable node/cluster SQL source must complete as `ok`, `empty` or a
manifest-declared `unsupported`; syntax/runtime SQL errors fail the test. It
also executes every declared host script over SSH and builds minimal one-shot
and three-sample snapshots reports in `local`, `remote-db-only` and `remote`.

## Legacy ClickHouse matrix

On a native amd64 host, run every pinned compatibility boundary:

```bash
python tools/run_legacy_clickhouse_matrix.py
```

Use `--boundary 20.3` repeatedly to select versions and `--remove` for an
ephemeral CI run. Containers are named deterministically and retained/reused by
default. On ARM64 the runner exits successfully with an explicit skip before
pulling images because the pinned legacy manifests are `linux/amd64` only.

Each boundary executes every applicable node SQL source and a packaged
one-shot lifecycle smoke. It verifies execution/syntax compatibility rather
than exact result values.

## Multi-node ClickHouse and Keeper

Build, seed and test the real `1 shard x 2 replicas` fixture:

```bash
python tools/run_multinode_clickhouse.py
```

See [`integration/multinode/README.md`](integration/multinode/README.md) for
ports, topology, reusable volumes and variants. The suite verifies both native
endpoints, Keeper metadata, replicated/distributed/local engines, every
applicable node and cluster SQL source, and cluster one-shot plus snapshots.

## Adding or correcting tests

- Change content contract tests with any intentional YAML/source rule change.
- Add version variants and a real boundary execution when ClickHouse releases
  differ in system-table columns or semantics.
- Add sampler parser fixtures for every supported old/new host-tool output.
- Add browser assertions for user-visible renderer controls or export changes.
- Keep unit tests offline, deterministic and independent of generated reports.
- Keep integration containers reusable locally and removable in CI; do not
  silently accept SQL errors as optional behavior.
- Fix implementation/content first when a stable assertion exposes a defect.
  Update an assertion only when the documented contract intentionally changed.
