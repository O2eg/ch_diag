from __future__ import annotations

import asyncio
import threading

from ch_diag.clickhouse import (
    ClickHouseAdapter,
    ConnectionConfig,
    TargetContext,
    classify_error,
    render_target_sql,
)
from ch_diag.collector import _sanitize_sensitive_result
from ch_diag.database_adapter import DatabaseAdapter


def test_tls_tunnel_preserves_original_server_hostname() -> None:
    config = ConnectionConfig(host="db.example", port=9440, secure=True)
    tunneled = config.tunneled("127.0.0.1", 42001)
    assert tunneled.host == "127.0.0.1"
    assert tunneled.port == 42001
    assert tunneled.server_hostname == "db.example"


def test_cluster_name_is_quoted_and_node_rejects_placeholder() -> None:
    sql = "SELECT * FROM clusterAllReplicas({{cluster}}, system.one)"
    rendered = render_target_sql(sql, TargetContext("cluster", "prod'cluster"))
    assert "'prod\\'cluster'" in rendered
    try:
        render_target_sql(sql, TargetContext("node"))
    except ValueError as exc:
        assert "placeholder" in str(exc)
    else:
        raise AssertionError("node query accepted a cluster placeholder")


def test_missing_identifier_is_unsupported_only_for_declared_capability() -> None:
    error = RuntimeError("Unknown identifier broken_column")
    assert classify_error(error) == "error"
    assert classify_error(error, optional_capability=True) == "unsupported"


def test_missing_zookeeper_hosts_is_an_optional_capability_error() -> None:
    error = RuntimeError("No hosts passed to ZooKeeper constructor")
    assert classify_error(error, optional_capability=True) == "unsupported"
    assert classify_error(error, optional_capability=False) == "error"


def test_sensitive_query_cells_are_bounded_and_literal_redacted() -> None:
    result = {
        "kind": "table",
        "columns": [{"name": "query"}, {"name": "normalized_query_hash"}],
        "rows": [["SELECT * FROM users WHERE password='hunter2' AND id=123", "42"]],
    }
    _sanitize_sensitive_result(result)
    query = result["rows"][0][0]
    assert "hunter2" not in query
    assert "123" not in query
    assert result["rows"][0][1] == "42"


class _BlockingClient:
    def __init__(self, state: dict[str, object]) -> None:
        self.state = state
        self.released = threading.Event()

    def execute(self, *_args: object, **_kwargs: object):
        lock = self.state["lock"]
        assert isinstance(lock, type(threading.Lock()))
        with lock:
            self.state["active"] = int(self.state["active"]) + 1
            self.state["maximum"] = max(
                int(self.state["maximum"]),
                int(self.state["active"]),
            )
        self.released.wait(3)
        with lock:
            self.state["active"] = int(self.state["active"]) - 1
        return [(1,)], [("value", "UInt8")]

    def cancel(self) -> None:
        self.released.set()

    def disconnect(self) -> None:
        self.released.set()


def _blocking_adapter(worker_count: int = 2):
    state: dict[str, object] = {
        "lock": threading.Lock(),
        "active": 0,
        "maximum": 0,
        "clients": [],
    }
    adapter = ClickHouseAdapter(
        ConnectionConfig(),
        worker_count=worker_count,
        close_timeout_seconds=2,
    )

    def client_factory() -> _BlockingClient:
        client = _BlockingClient(state)
        clients = state["clients"]
        assert isinstance(clients, list)
        clients.append(client)
        return client

    adapter._client = client_factory  # type: ignore[method-assign]
    return adapter, state


def test_clickhouse_adapter_satisfies_neutral_database_contract() -> None:
    adapter, _state = _blocking_adapter()
    try:
        assert isinstance(adapter, DatabaseAdapter)
    finally:
        asyncio.run(adapter.close())


def test_worker_pool_is_bounded_and_close_drains_every_worker() -> None:
    async def verify() -> None:
        adapter, state = _blocking_adapter(worker_count=2)
        tasks = [
            asyncio.create_task(adapter._execute_raw("SELECT 1", timeout_seconds=2))
            for _index in range(8)
        ]
        await asyncio.sleep(0.05)
        assert int(state["maximum"]) == 2
        clients = state["clients"]
        assert isinstance(clients, list)
        for client in clients:
            client.released.set()
        assert await asyncio.gather(*tasks) == [([(1,)], [("value", "UInt8")])] * 8
        await adapter.close()
        assert state["active"] == 0
        assert adapter._clients == {}
        assert not any(
            thread.name.startswith("ch_diag_clickhouse") and thread.is_alive()
            for thread in threading.enumerate()
        )

    asyncio.run(verify())


def test_query_timeout_cancels_driver_and_leaves_no_worker() -> None:
    async def verify() -> None:
        adapter, state = _blocking_adapter(worker_count=1)
        try:
            result = await adapter.execute_query(
                "SELECT sleep(10)",
                target=TargetContext("node"),
                timeout_seconds=0.02,
            )
            assert result["collection_status"] == "timeout"
        finally:
            await adapter.close()
        assert state["active"] == 0
        assert adapter._clients == {}

    asyncio.run(verify())
