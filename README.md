# ch_diag

`ch_diag` builds read-only diagnostic reports for ClickHouse. It collects
ClickHouse system tables and, when requested, Linux host data; the result is a
strict JSON artifact and/or a self-contained HTML report with Apache ECharts.
The installed package contains its SQL, shell scripts, renderer and JavaScript
assets and does not require `pg_diag`, a CDN or Internet access at runtime.

## Documentation

- [Content pack](https://github.com/O2eg/ch_diag/blob/main/ch_diag/content/README.md) —
  report layout, query/script/metric manifests, version variants, instructions
  and integrity boundary.
- [Tests](https://github.com/O2eg/ch_diag/blob/main/tests/README.md) — unit,
  browser, live ClickHouse, LTS-version and multi-node test commands.
- [Security model](https://github.com/O2eg/ch_diag/blob/main/docs/security.md) —
  read-only execution, credentials, redaction and report handling.
- [Compatibility matrix](https://github.com/O2eg/ch_diag/blob/main/docs/compatibility.md) —
  supported Python, ClickHouse and host-tool versions.
- [Troubleshooting query gap map](https://github.com/O2eg/ch_diag/blob/main/docs/troubleshooting_query_gap.md) —
  coverage of the ClickHouse troubleshooting knowledge base.

Quick navigation: [install](#install), [runtime requirements](#runtime-requirements),
[configuration](#configuration-and-precedence), [content inspection](#inspect-and-validate-content),
[collection modes](#collection-model), [SSH](#ssh-mode-and-known-hosts),
[item filters](#targeted-reports), [outputs](#output-and-metadata),
[report contents](#report-contents), [security](#safety-model), and
[tests](#tests-and-package-verification).

## Features

- LTS-anchored ClickHouse SQL variants starting with ClickHouse `20.3`.
- Node and real cluster collection through the native ClickHouse protocol.
- Point-in-time `one-shot` and repeated `snapshots` reports.
- Database-only, local-host and key-authenticated SSH collection modes.
- Declarative query, shell and metric items with exact ID and tag filtering.
- Read-only SQL, bounded results, explicit item statuses and progress output.
- Self-contained HTML with interactive tables and ECharts graphs, plus strict
  schema-v5 JSON for automation, ETL and LLM/agent review.
- Offline rendering, optional metadata stripping and JSON/HTML format selection.
- Bundled content and renderer assets; no dependency on `pg_diag`, a CDN or
  Internet access at runtime.

## Install

The package is not published yet. After publication the normal command will be:

```bash
python3 -m pip install ch-diag
ch-diag --version
```

Install the current checkout for development:

```bash
python3 -m venv .venv
.venv/bin/pip install -e '.[dev]'
.venv/bin/ch-diag validate
```

Python 3.10 or newer is required. Reports are ordinary files and can be opened
directly through `file://`.

The distribution name is `ch-diag`, the import package is `ch_diag`, and the
installed command is `ch-diag`. The wheel includes the content pack, schema,
HTML template and all JavaScript/CSS assets. The CLI can also be invoked from a
checkout with `python -m ch_diag.cli --help`.

## Runtime requirements

Collector runtime:

- Linux and Python 3.10 or newer.
- Python dependencies declared in `pyproject.toml`: `clickhouse-driver`,
  `AsyncSSH` and `PyYAML`.
- Direct or SSH-forwarded access to the ClickHouse native TCP endpoint; the
  HTTP interface is not used.

ClickHouse target:

- ClickHouse `20.3` or newer. SQL contracts are tested on explicit LTS branches;
  an intermediate server release uses the nearest preceding LTS contract (for
  example, `22.9` uses `22.8`).
- A dedicated account with `SELECT` on the required `system.*` tables. The
  driver requests `readonly=2` for every diagnostic connection.
- Cluster scope additionally requires the same usable account on every replica
  reached through `clusterAllReplicas` and a configured entry in
  `system.clusters`.

Full host collection in `local` or SSH `remote` mode requires Linux with
`/proc`, a POSIX shell and common base commands. The bundled probes use tools
from `procps` (`ps`, `sysctl`), `util-linux` (`lscpu`, `lsblk`), `iproute2`
(`ip`), libc/binutils (`ldd`), and core utilities such as `awk`, `df`, `mount`,
`readlink`, `sed`, `stat` and `uname`. Install `lshw` for the hardware sections;
the probes use passwordless `sudo -n` only when it is already available and
otherwise run `lshw` as the diagnostics user. `sysstat` supplies the packaged
`iostat` process used for disk throughput, IOPS, utilization and latency charts.
Disk sampling runs independently from the procfs CPU, memory and network probe,
so an unavailable `iostat` affects only the disk chart items.
The ClickHouse process probe also reads `/proc/PID/task`: per-TID CPU is
available with normal procfs access, while per-TID I/O can require the
diagnostics account to match the ClickHouse service user or have equivalent
ptrace permission. Linux RSS is intentionally not reported per thread because
ClickHouse threads share one process address space.

Missing host commands affect only the corresponding attempted item. Use
`remote-db-only` when host evidence is not required: no host script or sampler
is executed in that mode. The SSH target needs `sshd` and the host utilities,
but does not need Python, `ch_diag`, a virtual environment or copied collector
files.

## Configuration and precedence

Repeated automation can use a TOML file. `--config` is a global option and
must appear before the command:

```toml
# ~/.config/ch_diag/config.toml
[connection]
host = "clickhouse.example.net"
port = 9440
user = "ch_diag"
password_env = "CH_DIAG_PASSWORD"
secure = true
ca_certs = "/etc/ssl/certs/clickhouse-ca.pem"

[collection]
mode = "remote-db-only"
target_scope = "node"

[output]
directory = "reports/nightly"
formats = ["json", "html"]
strip_meta = true

[snapshots]
duration = 10
interval = 5
```

```bash
ch-diag --config ~/.config/ch_diag/config.toml snapshots
```

The deterministic precedence is `explicit CLI > CH_DIAG_* environment > TOML
> built-in defaults`. Lists supplied explicitly on the CLI replace configured
lists and can then be repeated. Supported environment names follow CLI names,
for example `CH_DIAG_HOST`, `CH_DIAG_PORT`, `CH_DIAG_COLLECTION_MODE`,
`CH_DIAG_TARGET_SCOPE`, `CH_DIAG_OUTPUT_FORMAT`, `CH_DIAG_SSH_HOST` and
`CH_DIAG_DURATION`. Run `ch-diag --help` and the command help for the full CLI.

Literal passwords are deliberately rejected in TOML. Put only
`password_env = "CH_DIAG_PASSWORD"` in the file and supply the secret through
that environment variable, or use `--password-prompt`.

## Inspect and validate content

The installed command uses the content pack bundled inside the `ch_diag`
package, independently of the current working directory. Validate it and
inspect the selectable report surface without connecting to ClickHouse:

```bash
ch-diag validate
ch-diag item-id-list
ch-diag tags-list

ch-diag explain-plan \
  --ch-version 25.8 \
  --run-mode snapshots \
  --collection-mode remote-db-only \
  --target-scope node
```

`explain-plan` prints JSON containing the selected version variant, SQL file,
planned/skipped state and reason for every visible item. `--content PATH` can
select another pack, but a content pack is executable input: its SQL and shell
sources must be trusted and its integrity manifest must match. A changed,
added or removed protected Python, shell, SQL or YAML file stops loading before
YAML is parsed. Markdown documentation and item instructions are deliberately
outside this executable-content checksum. Restore an unknown pack from a
trusted package rather than accepting its changes on a production collector.

## Collection model

Run mode, connection mode and SQL target scope are independent.
Both collection commands default to `local` plus node scope; specify both
dimensions explicitly in automation so host evidence cannot silently refer to
the wrong machine.

```text
remote-db-only

  ch-diag ---------------- native protocol ----------------> ClickHouse
     |                                                        node/cluster SQL
     +--> JSON + autonomous HTML

local

  collector host                                             ClickHouse
  +------------------+       native protocol                 +----------+
  | ch-diag          | ------------------------------------> | system.* |
  | Linux scripts    |                                       +----------+
  | Linux samplers   |
  +--------+---------+
           +--> JSON + autonomous HTML

remote

  collector                         SSH target / DB host
  +---------+   verified SSH key    +-----------------------------+
  | ch-diag | ====================> | SSH tunnel -> ClickHouse    |
  +---------+                       | Linux scripts and samplers  |
                                    +--------------+--------------+
                                                   +--> report data
```

Important: `local` means OS data is collected on the machine running
`ch-diag`, even if ClickHouse is in a container or on another TCP host. Use
`remote` when OS data must describe the database server. Cluster-wide SQL does
not imply OS fan-out: OS data still belongs only to the collector or one SSH
target and is labelled accordingly.

| Run mode | Connection mode | ClickHouse SQL | Host one-shot | Host charts |
|---|---|---:|---:|---:|
| `one-shot` | `local` | yes | collector host | no |
| `one-shot` | `remote-db-only` | yes | no | no |
| `one-shot` | `remote` | through SSH tunnel | SSH target | no |
| `snapshots` | `local` | repeated + one-shot | collector host | collector host |
| `snapshots` | `remote-db-only` | repeated + one-shot | no | no |
| `snapshots` | `remote` | through SSH tunnel | SSH target | SSH target |
| `render` | none | no | no | no |

Inapplicable items are not executed and do not appear in the report. Their
item id and reason are written to stdout and the optional run log together with
percentage progress.

### Collection timing

| Item/source type | `one-shot` | `snapshots` |
|---|---|---|
| Visible `query` | once | once before the sampling window |
| Visible host `script` | once in `local`/`remote` | once before the window in `local`/`remote` |
| ClickHouse `every_snapshot` metric source query | omitted | at every scheduled point |
| ClickHouse `window_end` metric source query | omitted | eligible once at the exact window-end deadline |
| Procfs CPU/memory/network and ClickHouse process/thread sampler | omitted | at every scheduled point in `local`/`remote` |
| `iostat` disk sampler | omitted | one independent window-length process in `local`/`remote` |
| Visible `metric` | omitted without execution | evaluated after sampling from its declared source |

The bundled pack uses `once`, `every_snapshot` and `window_end`. Procfs,
ClickHouse process/thread and each SQL source have independent loops driven by
the same absolute monotonic deadlines. SQL concurrency is bounded by
`runtime_policy.database_workers`. A slow or failed source therefore cannot
shift another source's samples. The same source is never overlapped with
itself: if it is still running at its next deadline, only that observation is
skipped and a `sample_skipped_source_busy` diagnostic is recorded. Every
successful observation carries its actual completion timestamp and counter
rates use the actual elapsed time between successful samples.

A counter reset, missing key or invalid value becomes a gap or diagnostic
rather than a negative or fabricated zero. The optional window-end
`system.query_thread_log` source correlates completed query threads with Linux
TIDs; it depends on `log_query_threads` and asynchronous log flushing, so
live/background evidence continues to come from procfs and ClickHouse thread
names.

`snapshots` defaults to `--duration 10 --interval 5`, scheduling offsets at
0, 5 and 10 seconds. The exact end of the window is always included; for
example `--duration 2 --interval 0.7` schedules 0, 0.7, 1.4 and 2 seconds. The
minimum interval is 0.2 seconds, duration must be at least the interval, and the
content policy limits a report to 360 scheduled samples. Snapshot markers keep
both the requested offset and actual monotonic offset. A source waiting for SQL
capacity or completing its final observation can make wall-clock runtime longer
than `--duration`. If a targeted snapshots plan contains only once-items, no
timed window is opened.

The independent `iostat` stream uses whole-second intervals and discards its
first cumulative-since-boot report. For sub-second snapshot settings it still
needs one real second, so a disk-targeted run can outlive the requested window;
other samplers keep their exact scheduled offsets and remain independent of an
`iostat` failure.

## First reports

Standalone node, database only:

```bash
ch-diag one-shot \
  --host clickhouse.example.net --port 9000 \
  --user ch_diag --password-prompt \
  --collection-mode remote-db-only \
  --target-scope node \
  --out-dir reports/node
```

Two or more derived datapoints in a short snapshots window:

```bash
ch-diag snapshots \
  --host clickhouse.example.net --port 9000 \
  --user ch_diag --password-prompt \
  --collection-mode remote-db-only \
  --target-scope node \
  --duration 2 --interval 1 \
  --out-dir reports/snapshots
```

`snapshots` takes samples at the beginning, each interval and the end. A
counter chart needs the initial endpoint plus later samples; resets become
gaps instead of negative rates.

Cluster-wide SQL uses an allow-listed name read from `system.clusters`:

```bash
ch-diag one-shot \
  --host coordinator.example.net --port 9000 \
  --collection-mode remote-db-only \
  --target-scope cluster --cluster-name AUTO \
  --out-dir reports/cluster
```

`AUTO` deterministically selects the first reported cluster. A literal name
must exist in `system.clusters`; `ALL` creates a separate file per cluster.
Node is the default and does not require a configured cluster.

## SSH mode and known hosts

SSH is key-only. `--ssh-known-hosts` is mandatory and host-key verification is
never silently disabled. Prepare a dedicated file before the first run:

```bash
mkdir -p ~/.ssh
chmod 700 ~/.ssh
ssh-keyscan -p 22 -t ed25519 -H db-host.example.net > ~/.ssh/ch_diag_known_hosts
chmod 600 ~/.ssh/ch_diag_known_hosts
ssh-keygen -lf ~/.ssh/ch_diag_known_hosts
```

`ssh-keyscan` retrieves a candidate key but does not authenticate it. Compare
the fingerprint with the server console, configuration inventory or an
administrator through a trusted channel. Then run:

```bash
ch-diag snapshots \
  --host 127.0.0.1 --port 9000 \
  --collection-mode remote --target-scope node \
  --ssh-host db-host.example.net --ssh-port 22 \
  --ssh-user chdiag --ssh-key ~/.ssh/ch_diag_ed25519 \
  --ssh-known-hosts ~/.ssh/ch_diag_known_hosts \
  --duration 10 --interval 5 \
  --out-dir reports/remote
```

`--host` and `--port` in this mode are resolved from the SSH target. The
ClickHouse native connection travels through the tunnel; shell scripts execute
on the SSH target.

## TLS

Root-CA verification:

```bash
ch-diag one-shot \
  --host clickhouse.example.net --port 9440 --secure \
  --ca-certs /etc/ssl/certs/clickhouse-ca.pem \
  --server-hostname clickhouse.example.net \
  --collection-mode remote-db-only --target-scope node
```

Mutual TLS additionally uses `--certfile` and `--keyfile`. `--no-verify` is an
explicit unsafe override and should only be used in a disposable test setup.
When TLS is tunneled over SSH, `--server-hostname` preserves verification of
the original ClickHouse hostname rather than the local tunnel address.

Prefer `--password-prompt` or `CH_DIAG_PASSWORD` to `--password VALUE`, because
command-line arguments can be visible in the process list. Passwords and key
material are not written to reports or logs.

## Targeted reports

`--item-id` and `--tags` accept a scalar, comma-separated values, or repeated
arguments and are mutually exclusive. Item IDs match exactly; tags match
case-insensitively with OR semantics (at least one requested tag).

```bash
ch-diag item-id-list
ch-diag tags-list

ch-diag one-shot ... \
  --item-id overview.server,dba_troubleshooting.storage_breakdown

ch-diag snapshots ... \
  --tags Snapshots,CPU
```

An unknown item or tag is a command error and is named explicitly. Use
`explain-plan --ch-version 25.8 ...` to inspect version/scope selection without
connecting to a server.

## Minimal diagnostics user

Use a dedicated read-only identity. A minimal current-version fixture can be
created by an administrator as follows; cluster mode requires the same user
and grants on every replica contacted by `clusterAllReplicas`:

```sql
CREATE USER ch_diag IDENTIFIED WITH sha256_password BY 'replace-me'
SETTINGS readonly = 2;
GRANT SELECT ON system.* TO ch_diag;
```

The driver also requests `readonly=2` and applies execution/result guards.
Some optional items may need access to a system table which is absent or not
granted in a particular edition; those items are classified as
`unsupported`/`permission_denied` rather than silently returning fabricated
data. Application tables do not need to be granted for the vendor report.

## Output and metadata

Both formats are produced by default under `--out-dir reports`. Select one or
both explicitly:

```bash
ch-diag one-shot ... --output-format html
ch-diag one-shot ... --output-format json
ch-diag one-shot ... --output-format html,json
```

`--json-out` and `--html-out` set exact paths for enabled formats; `--out-dir`
otherwise produces `report.json` and `report.html`. Cluster selector `ALL`
creates `report_<cluster>.json`/`.html` for every resolved cluster and therefore
cannot be combined with exact output paths. JSON and HTML are written atomically
with mode `0600`.

Progress is always flushed to stdout. Add `--log-file PATH` to append the same
timestamped lines to a mode-`0600` log; no log file is created by default. The
log contains start/finish records, percentage progress, item status and the
reason for every skipped or unsupported item. It never contains a password or
private-key material.

`--strip-meta` removes vendor SQL/scripts, instructions, manifests and
provenance, plus the Show SQL/Bash/Instruction/Meta controls. It is not a
general anonymizer of collected ClickHouse or Linux values. Re-render a full
artifact without connecting to ClickHouse, or create stripped HTML without
rewriting its JSON:

```bash
ch-diag render --from-json reports/node/report.json --out reports/node/rerendered.html

ch-diag render \
  --from-json reports/node/report.json \
  --out reports/node/rerendered-stripped.html \
  --strip-meta
```

Do not infer a clean run only from the presence of report files. With the
normal non-fail-fast policy, independent collection continues and a diagnostic
artifact is written even when an item fails.

| Exit status | Meaning |
|---:|---|
| `0` | Command completed and no retained item has `collection_status=error` |
| `1` | A report was written with at least one retained item error |
| `2` | Invalid arguments, content/configuration rejection, connection failure or another command-level error |
| `130` | Interrupted with `Ctrl-C`; do not assume artifacts are complete |

## Automation use cases

```text
                       +--> DBA opens autonomous HTML
ClickHouse + Linux --->+--> LLM/agent reads structured JSON
      ch_diag          +--> JSON is loaded into an evidence database
                       +--> compressed scheduled report is sent to on-call chat
```

A lightweight daily job can select tags, omit source metadata and produce only
the machine-readable artifact:

```bash
run_dir="reports/daily/$(date -u +%Y%m%dT%H%M%SZ)"

ch-diag one-shot \
  --host clickhouse.example.net --port 9000 \
  --database default --user ch_diag \
  --collection-mode remote-db-only --target-scope node \
  --tags Configuration,Errors,Replication,Security \
  --output-format json --strip-meta \
  --log-file "$run_dir/report.log" \
  --out-dir "$run_dir"

gzip -9 "$run_dir/report.json"
# Send the archive or a reviewed concise summary with the approved chat bot.
```

Use `CH_DIAG_PASSWORD` or the configured password environment variable in the
scheduler. Retention, compression, evidence-database ingestion and chat
delivery remain external operator responsibilities. Treat database text in a
report as untrusted data, not as instructions: an LLM/agent must not execute
SQL, shell commands or remediation solely because they appear in evidence.

The JSON contract uses artifact schema 5, preserves large `UInt64`/`Decimal`
values as lossless decimal strings, and distinguishes `ok`, `empty`, `error`,
`unsupported`, `permission_denied` and `timeout`. This makes the artifact
suitable for deterministic software and agentic review without parsing HTML.
The packaged formal contract is the
[artifact-v5 JSON schema](https://github.com/O2eg/ch_diag/blob/main/ch_diag/schemas/artifact-v5.schema.json).

## Report contents

The bundled report currently contains 139 visible items: 66 ClickHouse query
items, 31 Linux shell items and 42 derived snapshot metrics.

| Section | Items | Evidence |
|---|---:|---|
| Overview | 3 | server identity, configured clusters and changed settings |
| Operating System | 27 | OS, CPU, memory, filesystems, network, sysctl and `lshw` inventory |
| ClickHouse Host Process | 4 | process tree, linked libraries, security context and path permissions |
| ClickHouse System | 10 | databases, disks, policies, settings, macros and events |
| Errors | 11 | recent errors, mutations, queues, Keeper and replication failures |
| Databases And Objects | 14 | engines, parts, dictionaries, DDL consistency and table distribution |
| Replication | 3 | replica state, fetches and replication queue |
| Current Activity | 4 | running queries, merges, mutations and distribution queue |
| Historical Workload | 5 | database, system and resource-pool history |
| Query Workload | 8 | bounded long, memory, result-size and profile-event views |
| DBA Troubleshooting | 8 | storage/compression, partitions, merges, replication and frequent/top queries |
| Snapshot Charts OS | 12 | CPU, RAM, disk and network rates |
| Snapshot ClickHouse | 30 | query rate/latency, selected parts, file/network I/O, merges, caches, connections, background pools, MergeTree footprint, process/thread activity, Keeper and replication |

Availability depends on ClickHouse version, target scope, configured system
logs, grants, collection mode and host permissions. Cluster-only comparison
items have no fabricated node variant. Optional capabilities such as
`system.part_log` can be omitted as unsupported; an unexpected SQL column or
syntax failure remains an error.

## Content layout

```text
ch_diag/content/
  README.md            # content-pack contracts
  report.yaml          # report sections, item order, tags and runtime policy
  queries.yaml         # SQL manifests and version/scope variants
  scripts.yaml         # one-shot Linux shell manifests
  metrics.yaml         # snapshot metrics and sampler sources
  integrity.sha256     # protected content baseline
  queries/             # ClickHouse SQL files
  scripts/             # host probes, libraries and sampler scripts
  instructions/items/  # per-item DBA interpretation help
```

Each visible item references exactly one query, script or metric source.
Every SQL variant names its supported LTS branches and target scope explicitly;
the runtime does not rewrite a cluster query into a node query. SQL cursor metadata
defines table columns, while result contracts, units, limits and presentation
hints remain declarative. The effective content document and source provenance
are stored once in a normal artifact and are removed by `--strip-meta`.

The detailed contracts and reviewed update workflow are documented in the
[content-pack README](https://github.com/O2eg/ch_diag/blob/main/ch_diag/content/README.md).

## Safety model

- The driver session enforces ClickHouse `readonly=2`, execution timeout and
  result-row limits.
- Vendor SQL accepts only one `SELECT`, `WITH`, `SHOW` or `EXPLAIN` statement.
- Cluster names come from `system.clusters`, not raw SQL interpolation.
- Content SHA256 is verified before YAML, SQL or shell sources are loaded.
- HTML escapes report data and embeds pinned ECharts/highlight assets locally.
- Content integrity detects damage or replacement; it does not authenticate an
  attacker who can rewrite both installed Python and the checksum manifest.
- Runtime policy bounds targets, snapshots, result bytes, chart series and
  points. Deterministic chart truncation retains the newest points and emits a
  `chart_budget_truncated` diagnostic.

Use a dedicated ClickHouse diagnostics user with only required `system.*`
grants. Query log, DDL and exceptions can contain sensitive values; protect
generated files accordingly. The complete boundary and redaction rules are in
the [security model](https://github.com/O2eg/ch_diag/blob/main/docs/security.md).

## Compatibility

Python 3.10+ is the supported runtime; the built wheel is installed and
validated in a clean Python 3.10 container. SQL compatibility is tested only on
the pinned LTS branches `20.3`, `20.8`, `21.3`, `21.8`, `22.3`, `22.8`, `23.3`,
`23.8`, `24.3`, `24.8`, `25.3`, `25.8` and `26.3`. A non-LTS server uses the
nearest preceding LTS SQL contract; both the actual server version and selected
LTS branch are recorded in the artifact. Versions below `20.3` are rejected.

The full local integration baseline remains ClickHouse 25.8.28.1 on ARM64:
node and real two-replica Keeper cluster, verified TLS,
minimal/extended/denied privileges, and one-shot plus snapshots in `local`,
`remote-db-only` and SSH `remote` modes. The complete historical LTS matrix uses
pinned `linux/amd64` images in CI.

See the [compatibility matrix](https://github.com/O2eg/ch_diag/blob/main/docs/compatibility.md)
and [troubleshooting gap map](https://github.com/O2eg/ch_diag/blob/main/docs/troubleshooting_query_gap.md).

## Tests and package verification

```bash
.venv/bin/python -m compileall -q ch_diag
.venv/bin/ruff check ch_diag tests tools
.venv/bin/python tools/normalize_sql_outputs.py --check
.venv/bin/ch-diag validate
.venv/bin/pytest -q
.venv/bin/python -m pip install twine
.venv/bin/python -m build
.venv/bin/python -m twine check dist/*
```

Browser interaction tests use an optional dependency and a local Chromium:

```bash
.venv/bin/pip install '.[dev,browser]'
.venv/bin/python -m playwright install chromium
.venv/bin/pytest -q -m browser tests/browser
```

The reusable Docker fixture and live SQL test are described in
[tests/integration/docker/README.md](https://github.com/O2eg/ch_diag/blob/main/tests/integration/docker/README.md).
It installs SSH, `lshw`, `iostat` and `ip`, and keeps the container/data volume
between runs. The live test executes every applicable node SQL; only missing
capabilities declared in manifests may be treated as `unsupported`.

The [multi-node fixture](https://github.com/O2eg/ch_diag/blob/main/tests/integration/multinode/README.md)
starts two real replicas with a dedicated ClickHouse Keeper, seeds replicated,
Distributed and local-engine tables, and executes the complete node/cluster SQL
suite plus cluster one-shot and snapshots.

For visual review, the [report review harness](tools/report_review/README.md)
reuses that fixture to build a 12-case HTML/JSON matrix across all collection
modes, node/cluster scopes and one-shot/snapshots lifecycles, then writes a
clickable index and validates every HTML file in headless Chrome/Chromium.

The complete test map, minimum-Python container command and clean-wheel smoke
are in the [tests README](https://github.com/O2eg/ch_diag/blob/main/tests/README.md).

## License

The project code is MIT. Bundled renderer assets retain their licenses: Apache
ECharts (Apache-2.0), zrender (BSD-3-Clause) and highlight.js (BSD-3-Clause).
The complete package license expression is
`MIT AND BSD-3-Clause AND Apache-2.0`; corresponding license and notice files
are included in wheel and sdist.
