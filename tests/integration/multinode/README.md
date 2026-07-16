# Multi-node ClickHouse + Keeper fixture

This reusable integration module starts a real ClickHouse `25.8.28.1` cluster
with one shard, two replicas and a dedicated ClickHouse Keeper. The ClickHouse
nodes use the project's custom test image; Keeper uses the matching official
image.

```text
                    +-------------------------+
                    | ClickHouse Keeper       |
                    | keeper:9181             |
                    | host 127.0.0.1:19181    |
                    +------------+------------+
                                 |
                +----------------+----------------+
                |                                 |
      +---------v-----------+           +---------v-----------+
      | chdiag-node1        |           | chdiag-node2        |
      | replica=node1       |           | replica=node2       |
      | native host :19101  |           | native host :19102  |
      | SSH host :12301     |           | SSH host :12302     |
      +---------------------+           +---------------------+
```

The `chdiag_cluster` topology is `1 shard x 2 replicas`; macros and Keeper
paths are different for each node. All published ports are bound to loopback.

## Fixture data

Each run drops and recreates the Atomic database `chdiag_fixture`, then creates
and seeds:

- `ReplicatedMergeTree` data synchronized through Keeper;
- a `Distributed` table over the replicated table;
- node-local `MergeTree` rows on both replicas;
- `ReplacingMergeTree`, `TinyLog` and `Memory` tables;
- a distributed insert queue which is flushed before assertions.

The seed is intentionally small and deterministic. After synchronization both
replicas see six replicated rows, each node has two local rows, and the
Distributed table returns six rows. System logs are flushed so diagnostic SQL
has realistic metadata without a workload generator.

## Run

Prerequisites are Docker Compose and a development/test installation:

```bash
python3 -m venv .venv
.venv/bin/pip install -e '.[test]'
.venv/bin/python tools/run_multinode_clickhouse.py
```

The launcher:

1. builds or reuses the custom ClickHouse image;
2. starts Keeper and both nodes with stable names and volumes;
3. waits for Keeper TCP and both native endpoints;
4. recreates/seeds the fixture and synchronizes replication;
5. runs `test_multinode_clickhouse.py` and the generic live SQL module.

Useful variants:

```bash
# Reuse the already-built custom image.
.venv/bin/python tools/run_multinode_clickhouse.py --no-build

# Start and seed for manual investigation without pytest.
.venv/bin/python tools/run_multinode_clickhouse.py --skip-tests

# Run tests, then remove containers, network and named volumes.
.venv/bin/python tools/run_multinode_clickhouse.py --remove

# Allow more time on a slow builder.
.venv/bin/python tools/run_multinode_clickhouse.py --startup-timeout 300
```

`--no-build` requires the expected tagged image to exist. Containers and named
volumes are retained by default, but the test database is recreated on every
run; retained volumes speed startup rather than preserving fixture mutations.

## What is verified

- both real native endpoints answer and report their distinct hostnames;
- `system.clusters` and `clusterAllReplicas` expose exactly two replicas;
- Keeper metadata exists and both replicas are active/read-write;
- the replicated, Distributed and all local engine tables behave as expected;
- every applicable node- and cluster-scope SQL source executes without an
  unexpected syntax/runtime failure;
- cluster one-shot collection produces the selected topology, replication,
  distribution and troubleshooting items;
- cluster snapshots produce three samples and evaluate ClickHouse query-rate
  and replication-queue metrics.

The assertions intentionally do not compare complete diagnostic row contents.
They prove topology, syntax/execution and collection lifecycle while allowing
normal counters and timestamps to vary.

## Manual test commands and overrides

After `--skip-tests`, run the two modules directly:

```bash
CH_DIAG_TEST_HOST=127.0.0.1 \
CH_DIAG_TEST_PORT=19101 \
CH_DIAG_TEST_NODE2_PORT=19102 \
CH_DIAG_TEST_CLUSTER=chdiag_cluster \
  .venv/bin/pytest -q \
    tests/integration/test_multinode_clickhouse.py \
    tests/integration/test_live_clickhouse.py
```

The compose/launcher understands:

- `CLICKHOUSE_VERSION` and `CLICKHOUSE_VERSION_TAG`;
- `CHDIAG_KEEPER_PORT`;
- `CHDIAG_NODE1_NATIVE_PORT` and `CHDIAG_NODE2_NATIVE_PORT`;
- `CHDIAG_NODE1_SSH_PORT` and `CHDIAG_NODE2_SSH_PORT`.

The launcher forwards native/Keeper overrides into readiness and pytest. The
SSH ports are available for manual extension, but this fixture does not create
a client key or run the generic SSH/TLS lifecycle. That coverage belongs to the
[single-node fixture](../docker/README.md), keeping cluster failures focused on
ClickHouse/Keeper semantics.

Manual cleanup, including volumes:

```bash
docker compose \
  --project-name chdiag-multinode \
  --file tests/integration/multinode/compose.yaml \
  down --volumes
```
