from __future__ import annotations

import asyncio
import threading

import pytest

from ch_diag.clickhouse import (
    ClickHouseAdapter,
    ConnectionConfig,
    TargetContext,
    classify_error,
    failure_kind,
    render_target_sql,
)
from ch_diag.collector import _sanitize_sensitive_result
from ch_diag.database_adapter import DatabaseAdapter
from ch_diag.errors import ClickHouseIdentityChangedError


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


def test_clickhouse_failure_kinds_are_normalized_for_fallbacks() -> None:
    assert failure_kind(TimeoutError("query timed out")) == ("query_timeout", "exception_type")
    assert failure_kind(ConnectionResetError("connection reset by peer")) == (
        "transport_disconnect",
        "exception_type",
    )
    assert failure_kind(RuntimeError("Not enough privileges")) == (
        "permission_denied",
        "server_message",
    )
    assert failure_kind(RuntimeError("Unknown function normalizeQuery"), optional_capability=True) == (
        "unsupported_capability",
        "server_message",
    )
    assert failure_kind(RuntimeError("Query was cancelled")) == (
        "query_canceled",
        "server_message",
    )

    class ServerTimeout(RuntimeError):
        code = 159

    assert failure_kind(ServerTimeout("Timeout exceeded")) == (
        "query_timeout",
        "server_code",
    )


def test_unknown_function_is_unsupported_only_when_declared_optional() -> None:
    class UnknownFunctionError(RuntimeError):
        code = 46

    error = UnknownFunctionError("Function with name normalizeQuery does not exist")
    assert classify_error(error) == "error"
    assert classify_error(error, optional_capability=True) == "unsupported"


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


def test_query_settings_bound_source_reads_before_result_materialization() -> None:
    adapter = ClickHouseAdapter(
        ConnectionConfig(),
        max_query_rows_read=1234,
        max_query_bytes_read=5678,
    )
    try:
        settings = adapter._settings(2.5)
        assert settings["max_rows_to_read"] == 1234
        assert settings["max_bytes_to_read"] == 5678
        assert settings["read_overflow_mode"] == "throw"
    finally:
        asyncio.run(adapter.close())


def test_query_read_limit_failure_is_explicitly_incomplete() -> None:
    class LimitClient:
        def execute(self, *_args: object, **_kwargs: object):
            raise RuntimeError("Code: 158. Limit for rows to read exceeded: max_rows_to_read")

        def disconnect(self) -> None:
            pass

    async def verify() -> None:
        adapter = ClickHouseAdapter(ConnectionConfig())
        adapter._client = LimitClient  # type: ignore[method-assign]
        try:
            result = await adapter.execute_query(
                "SELECT * FROM system.query_log",
                target=TargetContext("node"),
            )
        finally:
            await adapter.close()

        assert result["collection_status"] == "error"
        assert result["diagnostics"][0]["code"] == "query_read_limit_exceeded"
        assert result["diagnostics"][0]["failure_kind"] == "read_limit"
        assert result["diagnostics"][0]["coverage_incomplete"] is True

    asyncio.run(verify())


def test_transport_disconnect_retries_once_after_identity_verification() -> None:
    async def verify() -> None:
        adapter = ClickHouseAdapter(
            ConnectionConfig(),
            reconnect_attempts=1,
            reconnect_delay_seconds=0,
        )
        adapter._identity = {
            "current_database": "default",
            "server_version": "25.8",
            "database_hostname": "clickhouse-1",
        }
        calls = 0

        async def execute_raw(_sql: str, **_kwargs: object):
            nonlocal calls
            calls += 1
            if calls == 1:
                raise ConnectionResetError("connection reset by peer")
            return [(1,)], [("value", "UInt8")]

        async def verify_identity() -> None:
            return None

        adapter._execute_raw = execute_raw  # type: ignore[method-assign]
        adapter._verify_reconnect_identity = verify_identity  # type: ignore[method-assign]
        try:
            result = await adapter.execute_query("SELECT 1", target=TargetContext("node"))
        finally:
            await adapter.close()

        assert result["collection_status"] == "ok"
        assert calls == 2

    asyncio.run(verify())


def test_reconnect_identity_change_refuses_to_mix_samples() -> None:
    async def verify() -> None:
        adapter = ClickHouseAdapter(ConnectionConfig())
        adapter._identity = {
            "current_database": "default",
            "server_version": "25.8",
            "database_hostname": "clickhouse-1",
        }

        async def read_context():
            return {
                "current_database": "default",
                "server_version": "25.8",
                "database_hostname": "clickhouse-2",
            }

        adapter._read_runtime_context = read_context  # type: ignore[method-assign]
        try:
            with pytest.raises(ClickHouseIdentityChangedError, match="refusing to merge samples"):
                await adapter._verify_reconnect_identity()
        finally:
            await adapter.close()

    asyncio.run(verify())


def test_each_fresh_driver_connection_is_identity_checked_before_query() -> None:
    class SwitchedClient:
        query_calls = 0

        def execute(self, sql: str, *_args: object, **_kwargs: object):
            if "currentDatabase()" in sql:
                return [
                    ("25.8", "default", "clickhouse-2")
                ], [
                    ("server_version", "String"),
                    ("current_database", "String"),
                    ("server_hostname", "String"),
                ]
            self.query_calls += 1
            return [(1,)], [("value", "UInt8")]

        def disconnect(self) -> None:
            pass

    async def verify() -> None:
        adapter = ClickHouseAdapter(ConnectionConfig())
        adapter._identity = {
            "current_database": "default",
            "server_version": "25.8",
            "database_hostname": "clickhouse-1",
        }
        client = SwitchedClient()
        adapter._client = lambda: client  # type: ignore[method-assign]
        try:
            result = await adapter.execute_query("SELECT 1", target=TargetContext("node"))
        finally:
            await adapter.close()

        assert result["collection_status"] == "error"
        assert "refusing to merge samples" in result["reason"]
        assert client.query_calls == 0

    asyncio.run(verify())
