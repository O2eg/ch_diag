# Official troubleshooting query gap map

Reviewed against the ClickHouse
[Useful queries for troubleshooting](https://clickhouse.com/docs/knowledgebase/useful-queries-for-troubleshooting)
page on 2026-07-16. External examples are adapted to bounded, typed, read-only items;
they are not copied blindly.

| Diagnostic | Disposition | ch_diag item / reason |
|---|---|---|
| Changed settings | covered | `overview.changed_settings` |
| Table sizes | covered | legacy `db_top_tables` and storage breakdown |
| Rows and daily growth | new_item P1 | deferred; requires safe date-range semantics |
| Compression and primary index | new_item P0 | `dba_troubleshooting.column_compression`, `storage_breakdown` |
| Queries per client | new_item P1 | deferred bounded historical item |
| Parts by partition | extend_existing P0 | `storage_breakdown`, `partition_part_counts` |
| Long-running current queries | covered | `activity.proc_current` |
| Query stack trace | optional_ad_hoc | deliberately excluded from automatic reports |
| Recent system errors | covered | `errors.errors_last`, `errors.errors_top` |
| Top CPU and memory queries | new_item P0 | `dba_troubleshooting.top_cpu_memory`; no raw query text |
| Projection size | new_item P1 | deferred capability-gated item |
| Disk/parts/rows/marks breakdown | new_item P0 | `dba_troubleshooting.storage_breakdown` |
| Recent level-0 parts | new_item P1 | deferred bounded item |
| Part creation rate | new_item P0 | optional `snapshot_charts_clickhouse.part_creation_rate` from `system.part_log` |
| Merges with ETA | extend_existing P0 | `dba_troubleshooting.merges_eta` |
| Frequent normalized query hash | new_item P0 | `dba_troubleshooting.frequent_queries` |
| Part creation errors | new_item P0 | optional `dba_troubleshooting.part_log_errors` |
| Number of tables by node | covered | cluster distribution legacy items |
| Async insert activity | new_item P1 | deferred bounded historical item |
| Active parts / excessive partitions | extend_existing P0 | `partition_part_counts` with raw rows and threshold flag |
| Detached parts | covered | `databases_objects.db_detached_parts` |
| Memory by node from query history | new_item P1 | deferred peak/average item |
| Running queries cluster-wide | covered | `activity.proc_current` cluster variant |
| Replication queue summary | extend_existing P0 | one-shot summary plus snapshot queue chart |

P1/P2 work does not block the preview release. Before each minor release this
map should be rechecked for new official candidates and duplication.
