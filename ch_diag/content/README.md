# ch_diag content pack

This directory contains the declarative report shipped with `ch_diag`. The
runtime loads and validates these files, selects a ClickHouse-version and target
scope variant, executes read-only SQL or trusted host probes, derives snapshot
charts and writes the same evidence to schema-v5 JSON and self-contained HTML.

The installed package uses this directory by default. A different directory is
loaded only when the operator explicitly selects it with `--content PATH`,
`CH_DIAG_CONTENT` or the TOML collection configuration.

## Layout

- `report.yaml` — report identity, runtime limits, tag vocabulary, section and
  item ordering, default expanded/collapsed state and source references.
- `queries.yaml` — ClickHouse query manifests, requirements, node/cluster and
  version variants, costs, privileges and result contracts.
- `scripts.yaml` — one-shot Linux shell source manifests and output contracts.
- `metrics.yaml` — snapshot metrics, sampler-provider registrations, series,
  transforms, units and chart contracts.
- `queries/` — SQL selected by query variants. `legacy/` preserves cluster SQL;
  `legacy_node/` contains reviewed node equivalents.
- `scripts/` — one-shot OS/ClickHouse-process probes, reusable shell libraries
  and repeated sampler scripts.
- `instructions/items/` — Markdown interpretation help embedded into normal
  artifacts and displayed by the HTML report.
- `UPSTREAM_OS_CONTENT.lock.yaml` — pinned provenance and hashes for Linux
  content synchronized from the reviewed `pg_diag` donor release.
- `integrity.sha256` — packaged baseline for executable/declarative content.

## Report items

Every visible item under `report.yaml:sections` has the canonical ID
`<section>.<item>` and references exactly one source:

```yaml
sections:
  overview:
    title: Overview
    items:
      server:
        query: overview.server
        tags: [Configuration, Cluster]
        state: expanded

  operating_system:
    title: Operating System
    items:
      os_release:
        script: os.os_release
        tags: [Configuration]

  snapshot_charts_clickhouse:
    title: Snapshot Charts ClickHouse
    items:
      query_rate:
        metric: clickhouse.query_rate
        tags: [Snapshots, Queries]
```

Item IDs are the public filter keys accepted by `--item-id`; source IDs are
internal catalog keys. Tags must come from `report.allowed_item_tags` and are
matched case-insensitively with OR semantics by `--tags`. `state` is
`expanded`, `collapsed` or `hidden` and controls only initial presentation.

The current pack contains query, script and metric items. It intentionally has
no trusted Python content sources: product-independent behavior belongs in the
runtime, while ClickHouse and Linux evidence remains declarative SQL/shell.

## Query manifests

A query source declares its stable result and execution contract once, then
lists explicit version/scope variants:

```yaml
queries:
  overview.server:
    title: ClickHouse Server Version
    description: Server version, hostname, database and user.
    variants:
    - id: overview_server_node
      min_ch_version: '20.3'
      scopes: [node]
      sql_file: overview/server_node.sql
    - id: overview_server_cluster
      min_ch_version: '20.3'
      scopes: [cluster]
      sql_file: overview/server_cluster.sql
    collection_scope: once
    cost_class: low
    privilege_profile: clickhouse_system_read
    result_contract:
      kind: table
      unit_policy: raw
      may_be_empty: true
```

Version intervals are half-open: `min_ch_version <= server < max_ch_version`.
Ranges for the same target scope may not overlap. A variant with no maximum is
open-ended. Node and cluster are explicit contracts; node SQL must not contain
the `{{cluster}}` placeholder, and the runtime does not invent a node query
from cluster SQL.

Cluster variants use only the `{{cluster}}` placeholder. The adapter resolves
the requested name through `system.clusters`, quotes it as a ClickHouse string
and substitutes it before execution. Do not introduce other template syntax or
interpolate object/user input into SQL.

`requires.tables` and `requires.columns` describe version/edition capabilities.
A missing declared capability becomes `unsupported`. Unexpected SQL syntax or
a missing identifier which was not declared as a capability remains an error so
a broken check cannot be hidden as compatibility behavior.

SQL files must contain one `SELECT`, `WITH`, `SHOW` or `EXPLAIN` statement.
Mutating statements, multiple statements and output-file constructs are
rejected during validation. Runtime execution additionally applies
`readonly=2`, time, row and byte limits.

Metric input queries are catalog entries too, but do not have visible query
items. Their `collection_scope` is `every_snapshot` and the planner includes
only sources required by selected metrics.

## Host script manifests

Script sources are one-shot items with `collection_scope: once`:

```yaml
scripts:
  clickhouse.linked_libraries:
    title: ClickHouse Server Linked Libraries
    file: clickhouse/linked_libraries.sh
    library: lib/clickhouse_process.sh
    output: plain_text
    timeout_seconds: 5
    collection_scope: once
    cost_class: low
    privilege_profile: host_read
    result_contract:
      kind: plain_text
      unit_policy: raw
      may_be_empty: true
```

Supported output conventions are `plain_text` and `table_json`. Table JSON must
be a JSON object or array that the generic executor can normalize into column
descriptors and rows. Scripts must be POSIX `/bin/sh`, bounded, non-mutating and
self-contained after any declared `library` is prepended.

In `local` mode script text runs on the collector. In `remote` mode the same
text is sent to `/bin/sh -s` over the existing verified SSH session; it cannot
depend on its package filename or sibling files at the target. In
`remote-db-only` mode host scripts are omitted without execution and their skip
reason is printed/logged.

ClickHouse-process probes receive the connected database address and native
port as runtime placeholders. The shared process library resolves the listening
socket and owning PID so the process tree, `ldd`, limits and permissions describe
the instance to which the native protocol connected rather than an arbitrary
ClickHouse process on a multi-instance host.

## Metrics and samplers

`metrics.yaml` registers opaque sampler outputs and visible metrics. A metric
references exactly one `source_query` or `source_sampler`, declares one or more
series, and uses a `gauge`, `delta` or `rate` transform. Units are raw in JSON;
adaptive K/M/G or byte scaling is presentation behavior in the renderer.

```yaml
metrics:
  clickhouse.query_rate:
    source_query: metrics.events
    series:
    - name: queries
      value_ref: queries
      transform: rate
      unit: queries/s
    chart:
      kind: line
      unit: queries/s
    collection_scope: every_snapshot
```

The bundled pack uses only `every_snapshot`: sources run at offsets zero, each
interval and the exact window end. Rates and deltas are calculated between
adjacent samples using actual elapsed time. Counter resets and invalid or
missing keys create gaps/diagnostics instead of negative values or fabricated
zeroes.

The `linux_os` provider exposes procfs CPU, memory, disk and network samples plus
the ClickHouse server process selected by the connected native port. Provider
implementation is generic runtime code; the commands and public output IDs are
declared here. `remote-db-only` excludes sampler-backed metrics, while SQL
metrics remain available.

## Instructions and metadata

The default instruction path for item `section.item` is:

```text
instructions/items/section/item.md
```

Instructions should explain what the item shows, important symptoms, common
causes and a safe DBA investigation checklist. They are embedded into normal
JSON/HTML and omitted by `--strip-meta`. Markdown is not executable and is not
covered by `integrity.sha256`; SQL, scripts and YAML remain protected.

Normal artifacts store the effective content document and provenance once, not
a duplicate manifest per item. Item metadata points to the relevant source,
variant and instruction. `--strip-meta` removes those sources, manifests,
instructions and provenance while preserving collected evidence and required
presentation hints.

## Modes and applicability

| Run/collection mode | Query items | Script items | SQL metrics | Host metrics |
|---|---:|---:|---:|---:|
| `one-shot remote-db-only` | once | omitted | omitted | omitted |
| `one-shot local` | once | collector host | omitted | omitted |
| `one-shot remote` | through tunnel | SSH target | omitted | omitted |
| `snapshots remote-db-only` | once | omitted | repeated | omitted |
| `snapshots local` | once | collector host once | repeated | collector host repeated |
| `snapshots remote` | through tunnel once | SSH target once | repeated | SSH target repeated |

Version-, scope- and mode-inapplicable items are not invoked and do not appear
in the final artifact. Their IDs and reasons remain visible in stdout and an
optional `--log-file`. Attempted empty, permission-denied, timeout and error
results remain visible because they are diagnostic evidence.

## Integrity and validation

Before parsing YAML, the loader verifies every `*.py`, `*.sh`, `*.sql`,
`*.yaml` and `*.yml` file recursively against `integrity.sha256`. Added,
removed or modified protected files disable collection without exposing old or
new hash values. The mechanism detects changes relative to the installed
baseline; package provenance and filesystem permissions remain necessary
because an attacker able to replace both runtime code and the manifest is
outside this boundary.

After a protected change has been reviewed and incorporated through the
release-maintainer workflow, run:

```bash
ch-diag validate
python tools/normalize_sql_outputs.py --check
python -m pytest -q tests/unit/test_content_and_planner.py
```

Validation checks duplicate YAML keys, schema version, item/source references,
tag/state values, safe relative paths, source files, read-only SQL shape,
version intervals, node/cluster scopes, source/result contracts, declared
requirements, sampler outputs and metric transforms. Real ClickHouse container
tests are still required: structural validation cannot prove that a SQL column
exists or has the same meaning in every server version.

When changing content, update the corresponding item instruction, unit
contract, current ClickHouse integration coverage and any affected legacy
boundary variant together. Do not edit synchronized Linux probes directly;
review donor changes and use the pinned synchronization workflow so
`UPSTREAM_OS_CONTENT.lock.yaml` remains auditable.
