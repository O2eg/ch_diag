from __future__ import annotations

import asyncio
import os
from pathlib import Path

import pytest
from clickhouse_driver import Client

from ch_diag.clickhouse import (
    ClickHouseAdapter,
    ConnectionConfig,
    TargetContext,
    create_clickhouse_adapter,
)
from ch_diag.collector import collect_one_shot, collect_snapshots
from ch_diag.content_loader import load_content
from ch_diag.host_scripts import load_host_script, render_host_script
from ch_diag.ssh_transport import SshConfig, SshSession
from ch_diag.versioning import ClickHouseVersion, select_variant


pytestmark = pytest.mark.integration


def live_config() -> ConnectionConfig:
    host = os.environ.get("CH_DIAG_TEST_HOST")
    if not host:
        pytest.skip("set CH_DIAG_TEST_HOST to run live ClickHouse tests")
    return ConnectionConfig(
        host=host,
        port=int(os.environ.get("CH_DIAG_TEST_PORT", "9000")),
        user=os.environ.get("CH_DIAG_TEST_USER", "default"),
        password=os.environ.get("CH_DIAG_TEST_PASSWORD"),
    )


def tls_config() -> ConnectionConfig:
    config = live_config()
    ca_cert = os.environ.get("CH_DIAG_TEST_TLS_CA")
    tls_port = os.environ.get("CH_DIAG_TEST_TLS_PORT")
    if not ca_cert or not tls_port:
        pytest.skip("set CH_DIAG_TEST_TLS_CA and CH_DIAG_TEST_TLS_PORT for live TLS")
    return ConnectionConfig(
        host=config.host,
        port=int(tls_port),
        user=config.user,
        password=config.password,
        secure=True,
        verify=True,
        ca_certs=ca_cert,
        server_hostname="127.0.0.1",
    )


def prepare_privilege_users() -> None:
    config = live_config()
    client = Client(host=config.host, port=config.port)
    try:
        client.execute("DROP TABLE IF EXISTS default.chdiag_privilege_probe")
        client.execute(
            "CREATE TABLE default.chdiag_privilege_probe (value UInt8) ENGINE=Memory"
        )
        client.execute("INSERT INTO default.chdiag_privilege_probe VALUES", [(1,)])
        for user in ("chdiag_minimal", "chdiag_extended", "chdiag_denied"):
            client.execute(f"DROP USER IF EXISTS {user}")
            client.execute(f"CREATE USER {user} IDENTIFIED WITH no_password")
        client.execute("GRANT SELECT ON system.* TO chdiag_minimal")
        client.execute("GRANT SELECT ON *.* TO chdiag_extended")
        client.execute("GRANT SELECT ON system.one TO chdiag_denied")
    finally:
        client.disconnect()


def live_ssh_config() -> SshConfig:
    key = os.environ.get("CH_DIAG_TEST_SSH_KEY")
    known_hosts = os.environ.get("CH_DIAG_TEST_SSH_KNOWN_HOSTS")
    if not key or not known_hosts:
        pytest.skip("set CH_DIAG_TEST_SSH_KEY and CH_DIAG_TEST_SSH_KNOWN_HOSTS")
    return SshConfig(
        host=os.environ.get("CH_DIAG_TEST_SSH_HOST", "127.0.0.1"),
        port=int(os.environ.get("CH_DIAG_TEST_SSH_PORT", "12222")),
        username=os.environ.get("CH_DIAG_TEST_SSH_USER", "chdiag"),
        client_key=key,
        known_hosts=known_hosts,
    )


async def assert_applicable_sql(scope: str, cluster_name: str | None = None) -> None:
    content = load_content()
    adapter = ClickHouseAdapter(live_config(), sql_timeout_seconds=15)
    try:
        context = await adapter.detect_runtime_context()
        version = ClickHouseVersion.parse(context["server_version"])
        failures = []
        target = TargetContext(scope, cluster_name)
        applicable = []
        unavailable = []
        executed = []
        for query_id, manifest in content.queries.items():
            variant = select_variant(
                list(manifest.get("variants") or []),
                version,
                scope,
                content.supported_lts_versions,
            )
            if variant is None:
                continue
            applicable.append(query_id)
            supported, _reason = await adapter.supports_requirements(manifest.get("requires"))
            if not supported:
                unavailable.append(query_id)
                continue
            sql = (content.path / "queries" / str(variant["sql_file"])).read_text(
                encoding="utf-8"
            )
            result = await adapter.execute_query(
                sql,
                target=target,
                timeout_seconds=float(manifest.get("timeout_seconds", 15)),
                optional_capability=bool(manifest.get("optional")),
            )
            executed.append(query_id)
            if result["collection_status"] not in {"ok", "empty", "unsupported"}:
                failures.append((query_id, result["collection_status"], result.get("reason")))
        assert set(executed) | set(unavailable) == set(applicable)
        assert applicable
        assert failures == [], "\n".join(
            f"{query_id}: {status}: {reason}"
            for query_id, status, reason in failures
        )
    finally:
        await adapter.close()


def test_every_applicable_node_sql_executes_without_runtime_error() -> None:
    asyncio.run(assert_applicable_sql("node"))


def test_every_applicable_cluster_sql_executes_without_runtime_error() -> None:
    cluster = os.environ.get("CH_DIAG_TEST_CLUSTER")
    if not cluster:
        pytest.skip("set CH_DIAG_TEST_CLUSTER to run cluster SQL tests")
    asyncio.run(assert_applicable_sql("cluster", cluster))


def test_live_tls_endpoint_verifies_certificate_and_collects() -> None:
    async def verify() -> None:
        adapter = ClickHouseAdapter(tls_config())
        try:
            context = await adapter.detect_runtime_context()
            assert context["database_engine"] == "clickhouse"
            result = await adapter.execute_query(
                "SELECT 1 AS tls_ok",
                target=TargetContext("node"),
            )
            assert result["collection_status"] == "ok"
            assert result["result"]["rows"] == [["1"]]
        finally:
            await adapter.close()

    asyncio.run(verify())


def test_minimal_extended_and_denied_privilege_contracts() -> None:
    prepare_privilege_users()

    async def verify() -> None:
        base = live_config()
        minimal = ClickHouseAdapter(ConnectionConfig(host=base.host, port=base.port, user="chdiag_minimal"))
        extended = ClickHouseAdapter(ConnectionConfig(host=base.host, port=base.port, user="chdiag_extended"))
        denied = ClickHouseAdapter(ConnectionConfig(host=base.host, port=base.port, user="chdiag_denied"))
        try:
            for adapter in (minimal, extended):
                context = await adapter.detect_runtime_context()
                assert context["read_only"] == "2"
                result = await adapter.execute_query(
                    "SELECT count() FROM system.tables",
                    target=TargetContext("node"),
                )
                assert result["collection_status"] == "ok"

            denied_result = await denied.execute_query(
                "SELECT count() FROM default.chdiag_privilege_probe",
                target=TargetContext("node"),
            )
            assert denied_result["collection_status"] == "permission_denied"

            mutation = await extended.execute_query(
                "CREATE TABLE default.chdiag_must_not_exist (value UInt8) ENGINE=Memory",
                target=TargetContext("node"),
            )
            assert mutation["collection_status"] in {"error", "permission_denied"}
        finally:
            await minimal.close()
            await extended.close()
            await denied.close()

    asyncio.run(verify())


def test_every_declared_host_script_executes_over_ssh() -> None:
    async def verify() -> None:
        content = load_content()
        session = await SshSession.connect(live_ssh_config())
        failures: list[tuple[str, int, str]] = []
        runtime_context = {"database_host_ip": "127.0.0.1", "database_port": 9000}
        try:
            for source_id, manifest in content.scripts.items():
                source = render_host_script(
                    load_host_script(content.path, manifest),
                    runtime_context,
                )
                result = await session.run_script(
                    source,
                    timeout=max(float(manifest.get("timeout_seconds", 3)), 10),
                )
                if result.returncode != 0:
                    failures.append((source_id, result.returncode, result.stderr[:500]))

            provider = content.sampler_providers["linux_os"]
            config = provider["config"]
            proc_source = render_host_script(
                (content.path / "scripts" / config["proc_script"]).read_text(encoding="utf-8"),
                runtime_context,
            )
            proc_result = await session.run_script(proc_source, timeout=5)
            if proc_result.returncode != 0:
                failures.append(("sampler.linux_proc", proc_result.returncode, proc_result.stderr[:500]))

            process_source = render_host_script(
                load_host_script(
                    content.path,
                    {"file": config["process_script"], "library": config["process_library"]},
                ),
                runtime_context,
            )
            process_result = await session.run_script(process_source, timeout=5)
            if process_result.returncode != 0:
                failures.append(
                    ("sampler.clickhouse_process", process_result.returncode, process_result.stderr[:500])
                )

            iostat = (content.path / "scripts" / config["iostat_script"]).read_text(encoding="utf-8")
            iostat_result = await session.run_script("set -- 1 2\n" + iostat, timeout=5)
            if iostat_result.returncode != 0:
                failures.append(("sampler.linux_iostat", iostat_result.returncode, iostat_result.stderr[:500]))
        finally:
            await session.close()
        assert failures == []

    asyncio.run(verify())


def test_collection_lifecycle_in_all_connection_modes(tmp_path: Path) -> None:
    async def verify() -> None:
        content = load_content()
        modes = {
            "remote-db-only": (live_config(), None),
            "local": (live_config(), None),
            "remote": (ConnectionConfig(host="127.0.0.1", port=9000), live_ssh_config()),
        }
        for mode, (connection, ssh_config) in modes.items():
            one_shot_ids = ["overview.server"]
            snapshot_ids = ["snapshot_charts_clickhouse.query_rate"]
            if mode != "remote-db-only":
                one_shot_ids.append("operating_system.os_release")
                snapshot_ids.extend(
                    [
                        "snapshot_charts_os.os_cpu_utilization",
                        "snapshot_charts_os.os_disk_read_throughput",
                        "snapshot_charts_clickhouse.process_memory",
                        "snapshot_charts_clickhouse.thread_pool_usage",
                    ]
                )

            one_shot_dir = tmp_path / mode / "one-shot"
            one_shot = await collect_one_shot(
                content,
                connection,
                out_dir=one_shot_dir,
                collection_mode=mode,
                target_scope="node",
                item_ids=one_shot_ids,
                output_formats=("json",),
                ssh_config=ssh_config,
                adapter_factory=create_clickhouse_adapter,
            )
            assert (one_shot_dir / "report.json").is_file()
            assert set(one_shot[0]["items"]) == set(one_shot_ids)
            assert all(
                item["collection_status"] in {"ok", "empty"}
                for item in one_shot[0]["items"].values()
            )

            snapshots_dir = tmp_path / mode / "snapshots"
            snapshots = await collect_snapshots(
                content,
                connection,
                out_dir=snapshots_dir,
                collection_mode=mode,
                target_scope="node",
                item_ids=snapshot_ids,
                output_formats=("json",),
                ssh_config=ssh_config,
                duration_seconds=0.4,
                interval_seconds=0.2,
                adapter_factory=create_clickhouse_adapter,
            )
            assert (snapshots_dir / "report.json").is_file()
            assert len(snapshots[0]["snapshots"]) == 3
            assert set(snapshots[0]["items"]) == set(snapshot_ids)
            assert all(
                item["collection_status"] in {"ok", "empty"}
                for item in snapshots[0]["items"].values()
            )

    asyncio.run(verify())
