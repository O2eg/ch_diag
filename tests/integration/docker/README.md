# Reusable single-node ClickHouse fixture

This custom ClickHouse image is the full live lifecycle fixture. It exposes a
plain native endpoint, a certificate-verifying TLS native endpoint and a
key-only SSH endpoint, and installs `lshw`, `sysstat`/`iostat`, `iproute2` and
the base tools used by host sources. The ClickHouse container and named data
volume are retained between iterations unless explicitly removed.

## Prerequisites and ports

- Docker Engine with the Compose plugin.
- A repository virtual environment with development dependencies.
- `ssh-keygen` and `ssh-keyscan` on the collector host.

```bash
python3 -m venv .venv
.venv/bin/pip install -e '.[dev]'
```

| Endpoint | Container | Collector endpoint used by tests |
|---|---:|---:|
| Native TCP | 9000 | `127.0.0.1:19001` |
| Native TLS | 9440 | `127.0.0.1:19440` |
| SSH | 22 | `127.0.0.1:12222` |

The compose short port syntax publishes these ports on Docker's default host
interfaces; the test commands connect through loopback. Use host firewall rules
or change the compose mappings if the workstation is on an untrusted network.

## Prepare and start

Generate a disposable test key. The entire ignored `state/` directory may be
deleted and recreated at any time:

```bash
mkdir -p tests/integration/docker/state
chmod 700 tests/integration/docker/state

ssh-keygen -q -t ed25519 -N '' \
  -f tests/integration/docker/state/id_ed25519
cp tests/integration/docker/state/id_ed25519.pub \
  tests/integration/docker/state/authorized_keys
chmod 600 tests/integration/docker/state/id_ed25519 \
  tests/integration/docker/state/authorized_keys
```

Build and start the fixture, then wait until the native endpoint answers:

```bash
docker compose -f tests/integration/docker/compose.yaml up -d --build

until docker exec chdiag-test-25-8 clickhouse-client --query 'SELECT 1'; do
  sleep 2
done
```

Export the generated test-only TLS trust anchor and record the SSH host key:

```bash
docker cp chdiag-test-25-8:/etc/clickhouse-server/tls/server.crt \
  tests/integration/docker/state/server.crt

ssh-keyscan -p 12222 -t ed25519 127.0.0.1 \
  > tests/integration/docker/state/known_hosts
chmod 600 tests/integration/docker/state/known_hosts
ssh-keygen -lf tests/integration/docker/state/known_hosts
```

The certificate and SSH key are created only for this disposable fixture. Do
not reuse their trust outside the test environment.

## Run the complete live module

Supply all endpoint and credential variables so none of the TLS/SSH lifecycle
coverage is skipped:

```bash
CH_DIAG_TEST_HOST=127.0.0.1 \
CH_DIAG_TEST_PORT=19001 \
CH_DIAG_TEST_CLUSTER=chdiag_test \
CH_DIAG_TEST_TLS_PORT=19440 \
CH_DIAG_TEST_TLS_CA=tests/integration/docker/state/server.crt \
CH_DIAG_TEST_SSH_HOST=127.0.0.1 \
CH_DIAG_TEST_SSH_PORT=12222 \
CH_DIAG_TEST_SSH_USER=chdiag \
CH_DIAG_TEST_SSH_KEY=tests/integration/docker/state/id_ed25519 \
CH_DIAG_TEST_SSH_KNOWN_HOSTS=tests/integration/docker/state/known_hosts \
  .venv/bin/pytest -q -m integration tests/integration/test_live_clickhouse.py
```

The module performs the following checks:

- every applicable node and single-node `chdiag_test` cluster SQL source
  executes without a syntax/runtime error;
- the TLS endpoint verifies against the exported certificate;
- `chdiag_minimal`, `chdiag_extended` and `chdiag_denied` are recreated and
  prove successful read-only collection, stable `permission_denied`
  classification and rejection of mutating SQL;
- every declared host script and the packaged procfs/process/`iostat` probes
  execute over the real SSH connection;
- targeted one-shot and three-sample snapshots reports complete in `local`,
  `remote-db-only` and SSH `remote` modes.

The suite checks execution contracts, not exact table values. Only
manifest-declared capabilities may become `unsupported`; unexpected SQL errors
fail the run.

## Reuse, versions and cleanup

Ordinary `up -d` and test reruns reuse the same named container and data volume.
Stop without deleting data:

```bash
docker compose -f tests/integration/docker/compose.yaml stop
```

Remove the container, network and data volume:

```bash
docker compose -f tests/integration/docker/compose.yaml down --volumes
```

The compose file accepts these overrides:

- `CLICKHOUSE_VERSION` — base image tag used by the build;
- `CLICKHOUSE_VERSION_TAG` — stable container/data-volume name component;
- `CLICKHOUSE_NATIVE_PORT` and `CLICKHOUSE_TLS_PORT` — host native ports;
- `CHDIAG_SSH_PORT` — host SSH port;
- `CHDIAG_TEST_PUBLIC_KEY_DIR` — directory containing `authorized_keys`.

Use a distinct version tag and ports to keep custom current-version fixtures
side by side. The pinned ClickHouse `20.3–26.3` LTS compatibility matrix is
handled by the dedicated runner below rather than this Dockerfile.

## LTS compatibility matrix

On a native amd64 machine, start and test all pinned LTS branches with:

```bash
.venv/bin/python tools/run_lts_clickhouse_matrix.py
```

Use `--branch 20.3` to run one branch; repeat the option to select several.
Containers have stable names/ports and are retained by default, so later runs
reuse them. Pass `--remove` for an ephemeral CI run. On ARM64 the command exits
successfully with an explicit skip before pulling images because the oldest
manifests are `linux/amd64` only.

GitHub Actions executes the 13 LTS branches from `20.3` through `26.3` as
separate native X64 matrix jobs. Each job runs every applicable node-scope SQL
source and a
packaged one-shot lifecycle smoke; result contents are not compared, but any
syntax/runtime SQL error fails the job.

The separate real cluster fixture is documented in
[`../multinode/README.md`](../multinode/README.md).
