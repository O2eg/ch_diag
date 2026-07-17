# Compatibility

Status as of 2026-07-17.

ClickHouse SQL compatibility is anchored only to LTS release branches. The
official policy marks LTS releases explicitly and says they are typically
published in March and August. Intermediate releases are not separate test or
SQL-variant targets: a server on such a release uses the nearest previously
released LTS contract.

Examples:

- ClickHouse `22.4` uses the `22.3` SQL contract;
- ClickHouse `22.9` uses the `22.8` SQL contract;
- ClickHouse `25.1` uses the `24.8` SQL contract;
- a release newer than the last listed LTS uses that last preceding LTS;
- releases older than `20.3` are unsupported because no preceding tested LTS
  contract exists.

The actual server version and the selected `sql_compatibility_lts` branch are
both recorded in report metadata.

| Component | Range | Tier |
|---|---|---|
| Python | 3.10+ | wheel validated in clean 3.10 container; CI on 3.10–3.13 |
| clickhouse-driver | 0.2.7+ | supported native protocol adapter |
| ClickHouse LTS | 20.3, 20.8, 21.3, 21.8, 22.3, 22.8, 23.3, 23.8, 24.3, 24.8, 25.3, 25.8, 26.3 | pinned node-SQL CI matrix |
| non-LTS ClickHouse | 20.3 or newer | nearest preceding LTS SQL contract |
| ClickHouse 25.8.28.1 ARM64 | node, TLS/SSH and `1 shard x 2 replicas` Keeper cluster | full local integration baseline |
| Linux | procfs plus POSIX shell | supported host sampler |
| ClickHouse Linux threads | `/proc/PID/task` stat plus permission-dependent I/O | parser, rate/reset and top-table aggregation tested |
| query_thread_log | Nested ProfileEvents through LTS 24.8; Map from LTS 25.3 | optional window-end CPU/I/O correlation variants |
| lshw | old/new JSON object or array output | parser/runtime tested on 02.19 |
| iostat | older and current sysstat headers | parser and independent disk sampler tested |

The 25.8 local matrix executes every applicable node and cluster SQL source,
all declared host scripts through SSH, one-shot and three-sample snapshots in
`local`, `remote-db-only` and `remote` modes, minimal/extended/denied privilege
profiles, certificate-verifying TLS, and browser interactions/exports. The
multi-node fixture uses real ReplicatedMergeTree, Distributed and local-engine
tables backed by a dedicated Keeper.

Every query variant declares explicit `lts_versions`. For each declared target
scope the content validator requires exactly one variant for every supported
LTS branch. Missing optional tables such as `system.part_log` are omitted only
when their manifest declares the capability optional. An unknown column in a
normal item is an error, so broken SQL cannot be hidden as an expected
compatibility skip.

## Pinned LTS container images

The SQL matrix uses exact tags and manifest digests rather than mutable branch
tags. The oldest images have no ARM64 layer, so the complete historical matrix
requires native `linux/amd64`; lack of an ARM64 image is a platform limitation,
not proof of SQL compatibility.

| LTS | Image | Manifest digest |
|---|---|---|
| 20.3 | `yandex/clickhouse-server:20.3.21.2` | `sha256:e9c704ac6dc7f11e09b3c00d784625ac6f7c4fe9c9050c1d4b61b572f2bdd434` |
| 20.8 | `yandex/clickhouse-server:20.8.18.32` | `sha256:e193a420c28c1ea0f2148e22b0b86cd8876e3b9f15015caa11862961e90d1aaa` |
| 21.3 | `yandex/clickhouse-server:21.3.20.1` | `sha256:4eccfffb01d735ab7c1af9a97fbff0c532112a6871b2bb5fe5c478d86d247b7e` |
| 21.8 | `clickhouse/clickhouse-server:21.8.15.7` | `sha256:a9141f199e4b1f60cd6fe5ee58e25a86938117d26a73c4a1fa5c31b6e2f64abf` |
| 22.3 | `clickhouse/clickhouse-server:22.3.20.29` | `sha256:f423f63c3d73f567a89cf919f61f38734e9df014f160826a22ffc3c730988218` |
| 22.8 | `clickhouse/clickhouse-server:22.8.21.38` | `sha256:015a65bf1cef750052c2456dd41af853d8ca65417a3cc564a7577a15c21ad479` |
| 23.3 | `clickhouse/clickhouse-server:23.3.22.3` | `sha256:40b254d736660c604b2e0d89511f156bdecffa634874687f59abb03d95a575ed` |
| 23.8 | `clickhouse/clickhouse-server:23.8.16.40` | `sha256:67307e3248b4acffe032515bb5dd26b8ba447bf9981ad50cbec326d40b1801a6` |
| 24.3 | `clickhouse/clickhouse-server:24.3.18.7` | `sha256:85b97f63dcfff47790d26bb5d5801637aaddb2b93e5e9aee27a686c2fb2b9916` |
| 24.8 | `clickhouse/clickhouse-server:24.8.14.39` | `sha256:1ffa82edee000a42c09313bd9f1293d94c570aee74babc1b3ca9983a35fa597b` |
| 25.3 | `clickhouse/clickhouse-server:25.3.14.14` | `sha256:b627d7a9bc0e0c1bac26cdbe9d2fc6316faa29c5d8a174f28f5abd57d0fa6ba2` |
| 25.8 | `clickhouse/clickhouse-server:25.8.28.1` | `sha256:a9d328123ff8a61bf6b16448528b577d59deb85758172e13b09054b0727f8adf` |
| 26.3 | `clickhouse/clickhouse-server:26.3.17.4` | `sha256:85c434814ac8905e5648027ce926f74ab067edd6aadbccb6c0c165cd3571ea49` |

GitHub Actions runs the 13 branches as independent X64 matrix jobs. Run the
same pinned matrix locally with:

```bash
python tools/run_lts_clickhouse_matrix.py
```

Use `--branch 22.8` repeatedly to select branches and `--remove` for ephemeral
containers. On an incompatible architecture the runner exits before pulling
images.

References: [ClickHouse Support Services Policy](https://clickhouse.com/legal/support-services-policy/archive/202501),
[official ClickHouse releases](https://github.com/ClickHouse/ClickHouse/releases).
