# Compatibility

Status as of 2026-07-16.

| Component | Range | Tier |
|---|---|---|
| Python | 3.10+ | wheel validated in clean 3.10 container; suite run on 3.12 |
| clickhouse-driver | 0.2.7+ | supported native protocol adapter |
| ClickHouse 25.8.28.1 ARM64 | node, verified TLS/SSH and `1 shard x 2 replicas` cluster with Keeper | tested locally |
| ClickHouse 22.2–25.x | declarative variants available | best effort outside 25.8 |
| ClickHouse 20.3–21.11 | retained legacy boundary variants | best effort; amd64 matrix required |
| Linux | procfs plus POSIX shell | supported host sampler |
| lshw | old/new JSON object or array output | parser/runtime tested on 02.19 |
| iostat | legacy and current sysstat headers | parser tested; procfs is the primary disk sampler |

The 25.8 local matrix executes every applicable node and cluster SQL source,
all declared host scripts through SSH, one-shot and three-sample snapshots in
`local`, `remote-db-only` and `remote` modes, minimal/extended/denied privilege
profiles, certificate-verifying TLS, and browser interactions/exports. The
multi-node fixture uses real ReplicatedMergeTree, Distributed and local-engine
tables backed by a dedicated Keeper.

The server version tuple is compared numerically and version intervals are
half-open (`min <= version < max`). Missing optional tables such as
`system.part_log` are omitted only when their manifest declares the capability
optional. An unknown column in a normal item is an error, so broken SQL cannot
be hidden as an expected compatibility skip.

Old ClickHouse images frequently have no ARM64 layer. Their compatibility must
be checked on a pinned `linux/amd64` runner; absence of an ARM64 image is a
platform limitation, not proof that SQL is compatible.

## Legacy container images

The legacy boundary images still exist on Docker Hub, but all manifests below
are `linux/amd64` only. Use exact versions or digests for the compatibility
matrix instead of mutable branch tags.

| Boundary | Image | Manifest digest |
|---|---|---|
| 20.3 | `yandex/clickhouse-server:20.3.21.2` | `sha256:e9c704ac6dc7f11e09b3c00d784625ac6f7c4fe9c9050c1d4b61b572f2bdd434` |
| 20.11 | `yandex/clickhouse-server:20.11.6.6` | `sha256:d728866bd5527c0295dda3f81387f2aa859704a069484395bc9bd3c382e167fa` |
| 21.1 | `yandex/clickhouse-server:21.1.9.41` | `sha256:4d9d04a76931b5d8fc123006b7e1f89fd73275879fdc4aaa13009aafdc3fddde` |
| 21.4 | `yandex/clickhouse-server:21.4.7.3` | `sha256:399f58d0c7680903c56ef3c536334b26b057cb166e169165d52307a4a765035c` |
| 21.8 | `clickhouse/clickhouse-server:21.8.15.7` | `sha256:a9141f199e4b1f60cd6fe5ee58e25a86938117d26a73c4a1fa5c31b6e2f64abf` |
| 21.11 | `clickhouse/clickhouse-server:21.11.11.1` | `sha256:a3c17fb19954ceb084d6227a7270ab2255570da5e47e64640586762496403d09` |
| 22.2 | `clickhouse/clickhouse-server:22.2.3.5` | `sha256:3eb11dccb5cae84da3edb1b97075e037f70265b0c13273d01622f3f2a088ce96` |

On an ARM64 workstation Docker must have an amd64 emulation handler and the
container must be started with `--platform linux/amd64`. A native amd64 CI
runner is preferred because emulation is slower and can introduce a platform
failure unrelated to ClickHouse SQL compatibility.

The GitHub Actions legacy job runs these seven boundaries automatically and in
parallel when `runner.arch == 'X64'`. The same pinned matrix can be invoked
locally with `python tools/run_legacy_clickhouse_matrix.py`; it explicitly
skips before pulling images on an incompatible architecture.
