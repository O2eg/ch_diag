from __future__ import annotations

import asyncio
import os
from pathlib import Path

import pytest

from ch_diag.clickhouse import ClickHouseAdapter, ConnectionConfig, create_clickhouse_adapter
from ch_diag.collector import collect_one_shot, collect_snapshots
from ch_diag.content_loader import load_content


pytestmark = pytest.mark.integration
CLUSTER = "chdiag_cluster"


def config(port: int | None = None) -> ConnectionConfig:
    host = os.environ.get("CH_DIAG_TEST_HOST")
    if not host:
        pytest.skip("set CH_DIAG_TEST_HOST to run multi-node ClickHouse tests")
    selected_port = port or int(os.environ.get("CH_DIAG_TEST_PORT", "19101"))
    return ConnectionConfig(host=host, port=selected_port)


async def query(sql: str, *, port: int | None = None) -> list[tuple[object, ...]]:
    adapter = ClickHouseAdapter(config(port), sql_timeout_seconds=15)
    try:
        rows, _columns = await adapter._execute_raw(sql, timeout_seconds=15)
        return rows
    finally:
        await adapter.close()


def test_cluster_has_one_shard_and_two_real_replicas() -> None:
    async def verify() -> None:
        adapter = ClickHouseAdapter(config())
        try:
            clusters = await adapter.list_clusters()
        finally:
            await adapter.close()
        selected = next(item for item in clusters if item["name"] == CLUSTER)
        assert selected == {"name": CLUSTER, "replicas": 2, "shards": 1}
        rows = await query(
            "SELECT hostName() FROM clusterAllReplicas('chdiag_cluster', system.one) "
            "ORDER BY hostName()"
        )
        assert [row[0] for row in rows] == ["chdiag-node1", "chdiag-node2"]

    asyncio.run(verify())


def test_fixture_covers_multiple_engines_and_both_local_nodes() -> None:
    async def verify() -> None:
        rows = await query(
            "SELECT hostName(), groupUniqArray(engine) "
            "FROM clusterAllReplicas('chdiag_cluster', system.tables) "
            "WHERE database = 'chdiag_fixture' GROUP BY hostName() ORDER BY hostName()"
        )
        assert len(rows) == 2
        required = {
            "ReplicatedMergeTree",
            "Distributed",
            "MergeTree",
            "ReplacingMergeTree",
            "TinyLog",
            "Memory",
        }
        for _host, engines in rows:
            assert required <= set(engines)

        local_rows = await query(
            "SELECT hostName(), count() FROM "
            "clusterAllReplicas('chdiag_cluster', chdiag_fixture.local_events) "
            "GROUP BY hostName() ORDER BY hostName()"
        )
        assert local_rows == [("chdiag-node1", 2), ("chdiag-node2", 2)]

    asyncio.run(verify())


def test_replication_distributed_table_and_keeper_are_live() -> None:
    async def verify() -> None:
        replicated = await query(
            "SELECT hostName(), count() FROM "
            "clusterAllReplicas('chdiag_cluster', chdiag_fixture.replicated_events) "
            "GROUP BY hostName() ORDER BY hostName()"
        )
        assert replicated == [("chdiag-node1", 6), ("chdiag-node2", 6)]

        distributed = await query("SELECT count() FROM chdiag_fixture.distributed_events")
        assert distributed == [(6,)]

        replicas = await query(
            "SELECT hostName(), total_replicas, active_replicas, is_readonly "
            "FROM clusterAllReplicas('chdiag_cluster', system.replicas) "
            "WHERE database = 'chdiag_fixture' AND table = 'replicated_events' "
            "ORDER BY hostName()"
        )
        assert replicas == [
            ("chdiag-node1", 2, 2, 0),
            ("chdiag-node2", 2, 2, 0),
        ]

        keeper = await query(
            "SELECT count() FROM system.zookeeper "
            "WHERE path = '/clickhouse/tables/01/chdiag_fixture/replicated_events'"
        )
        assert keeper[0][0] > 0

    asyncio.run(verify())


def test_both_nodes_serve_native_protocol() -> None:
    node2_port = int(os.environ.get("CH_DIAG_TEST_NODE2_PORT", "19102"))

    async def verify() -> None:
        node1 = await query("SELECT hostName(), version()")
        node2 = await query("SELECT hostName(), version()", port=node2_port)
        assert node1[0][0] == "chdiag-node1"
        assert node2[0][0] == "chdiag-node2"
        assert node1[0][1] == node2[0][1]

    asyncio.run(verify())


def test_ch_diag_collects_real_cluster_one_shot_and_snapshots(tmp_path: Path) -> None:
    async def verify() -> None:
        content = load_content()
        one_shot = await collect_one_shot(
            content,
            config(),
            out_dir=tmp_path / "one-shot",
            collection_mode="remote-db-only",
            target_scope="cluster",
            cluster_name=CLUSTER,
            item_ids=[
                "overview.clusters",
                "replication.repl_tables",
                "databases_objects.db_distr_by_hosts",
                "dba_troubleshooting.replication_summary",
            ],
            output_formats=("json",),
            adapter_factory=create_clickhouse_adapter,
        )
        assert len(one_shot) == 1
        assert all(
            item["collection_status"] in {"ok", "empty"}
            for item in one_shot[0]["items"].values()
        )

        snapshots = await collect_snapshots(
            content,
            config(),
            out_dir=tmp_path / "snapshots",
            collection_mode="remote-db-only",
            target_scope="cluster",
            cluster_name=CLUSTER,
            item_ids=[
                "snapshot_charts_clickhouse.query_rate",
                "snapshot_charts_clickhouse.replication_queue",
            ],
            output_formats=("json",),
            duration_seconds=0.4,
            interval_seconds=0.2,
            adapter_factory=create_clickhouse_adapter,
        )
        assert len(snapshots[0]["snapshots"]) == 3
        assert all(
            item["collection_status"] in {"ok", "empty"}
            for item in snapshots[0]["items"].values()
        )

    asyncio.run(verify())
