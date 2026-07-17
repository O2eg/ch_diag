"""ClickHouse native-protocol adapter used by the autonomous collector."""

from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, replace
import math
import json
import re
import threading
import time as time_module
from typing import Any
from uuid import uuid4

from .artifact_schema import column_descriptor
from .database_adapter import DatabaseTarget
from .errors import ClickHouseConnectionError
from .runtime_config import (
    DEFAULT_DATABASE_CLOSE_TIMEOUT_SECONDS,
    DEFAULT_DATABASE_WORKERS,
    DEFAULT_MAX_RESULT_BYTES,
    DEFAULT_MAX_RESULT_ROWS,
    DEFAULT_SQL_TIMEOUT_SECONDS,
)
from .serialization import json_safe
from .versioning import ClickHouseVersion

# Compatibility alias retained for integrations that imported the old name.
TargetContext = DatabaseTarget
_SECRET_RE = re.compile(
    r"(?i)(password|passwd|secret|token|private[_ -]?key)(\s*[=:]\s*)([^\s,;]+)"
)


def _driver():
    try:
        from clickhouse_driver import Client  # type: ignore
    except ModuleNotFoundError as exc:
        raise ClickHouseConnectionError(
            "clickhouse-driver is not installed; install the ch-diag package dependencies"
        ) from exc
    return Client


@dataclass(frozen=True)
class ConnectionConfig:
    host: str = "127.0.0.1"
    port: int = 9000
    database: str = "default"
    user: str = "default"
    password: str | None = None
    secure: bool = False
    verify: bool = True
    ca_certs: str | None = None
    certfile: str | None = None
    keyfile: str | None = None
    server_hostname: str | None = None
    connect_timeout: float = 5.0
    send_receive_timeout: float = 10.0

    def tunneled(self, host: str, port: int) -> "ConnectionConfig":
        server_hostname = self.server_hostname
        if self.secure and not server_hostname:
            server_hostname = self.host
        return replace(self, host=host, port=port, server_hostname=server_hostname)


class ClickHouseAdapter:
    def __init__(
        self,
        config: ConnectionConfig,
        *,
        sql_timeout_seconds: float = DEFAULT_SQL_TIMEOUT_SECONDS,
        max_result_rows: int = DEFAULT_MAX_RESULT_ROWS,
        max_result_bytes: int = DEFAULT_MAX_RESULT_BYTES,
        worker_count: int = DEFAULT_DATABASE_WORKERS,
        close_timeout_seconds: float = DEFAULT_DATABASE_CLOSE_TIMEOUT_SECONDS,
    ) -> None:
        self.config = config
        self.sql_timeout_seconds = float(sql_timeout_seconds)
        self.max_result_rows = int(max_result_rows)
        self.max_result_bytes = int(max_result_bytes)
        if int(worker_count) < 1:
            raise ValueError("ClickHouse worker_count must be at least 1")
        self.worker_count = int(worker_count)
        self.close_timeout_seconds = float(close_timeout_seconds)
        self._capability_cache: dict[tuple[str, str], bool] = {}
        self._executor = ThreadPoolExecutor(
            max_workers=self.worker_count,
            thread_name_prefix="ch_diag_clickhouse",
        )
        self._clients: dict[int, Any] = {}
        self._clients_lock = threading.Lock()
        self._closed = False

    def _client(self):
        Client = _driver()
        kwargs: dict[str, Any] = {
            "host": self.config.host,
            "port": int(self.config.port),
            "database": self.config.database,
            "user": self.config.user,
            "password": self.config.password or "",
            "secure": self.config.secure,
            "verify": self.config.verify,
            "connect_timeout": self.config.connect_timeout,
            "send_receive_timeout": self.config.send_receive_timeout,
            "settings_is_important": True,
        }
        for key in ("ca_certs", "certfile", "keyfile", "server_hostname"):
            value = getattr(self.config, key)
            if value:
                kwargs[key] = value
        return Client(**kwargs)

    def _settings(self, timeout_seconds: float | None = None) -> dict[str, Any]:
        timeout = float(timeout_seconds or self.sql_timeout_seconds)
        return {
            "readonly": 2,
            "max_execution_time": max(1, int(math.ceil(timeout))),
            "max_result_rows": self.max_result_rows,
            "max_result_bytes": self.max_result_bytes,
            "result_overflow_mode": "throw",
            "skip_unavailable_shards": 0,
        }

    async def detect_runtime_context(self) -> dict[str, Any]:
        query = (
            "SELECT version() AS server_version, currentDatabase() AS current_database, "
            "currentUser() AS current_user, hostName() AS server_hostname"
        )
        rows, columns = await self._execute_raw(query, timeout_seconds=self.sql_timeout_seconds)
        if not rows:
            raise ClickHouseConnectionError("ClickHouse runtime context query returned no rows")
        values = dict(zip((name for name, _type in columns), rows[0]))
        raw_version = str(values["server_version"])
        parsed = ClickHouseVersion.parse(raw_version)
        readonly_rows, _ = await self._execute_raw(
            "SELECT value FROM system.settings WHERE name = 'readonly'",
            timeout_seconds=self.sql_timeout_seconds,
        )
        readonly = str(readonly_rows[0][0]) if readonly_rows else "unknown"
        if readonly not in {"1", "2"}:
            raise ClickHouseConnectionError(
                f"ClickHouse connection did not confirm read-only mode (readonly={readonly})"
            )
        return {
            "database_engine": "clickhouse",
            "server_version": raw_version,
            "server_version_tuple": parsed.as_list(),
            "current_database": json_safe(values["current_database"]),
            "current_user": json_safe(values["current_user"]),
            "database_name": json_safe(values["current_database"]),
            "database_hostname": json_safe(values["server_hostname"]),
            "database_host_ip": self.config.host,
            "database_port": self.config.port,
            "read_only": readonly,
        }

    async def list_clusters(self) -> list[dict[str, Any]]:
        query = (
            "SELECT cluster, count() AS replicas, countDistinct(shard_num) AS shards "
            "FROM system.clusters GROUP BY cluster ORDER BY replicas DESC, cluster"
        )
        rows, _columns = await self._execute_raw(query)
        return [
            {"name": str(row[0]), "replicas": int(row[1]), "shards": int(row[2])}
            for row in rows
        ]

    async def supports_requirements(
        self,
        requirements: dict[str, Any] | None,
    ) -> tuple[bool, str | None]:
        required = requirements or {}
        missing: list[str] = []
        for table in required.get("tables") or []:
            database, name = _split_qualified_name(str(table), "table")
            if not await self._catalog_object_exists("table", database, name):
                missing.append(f"table {database}.{name}")
        for column in required.get("columns") or []:
            database, table, name = _split_qualified_name(str(column), "column")
            key = ("column", f"{database}.{table}.{name}")
            exists = self._capability_cache.get(key)
            if exists is None:
                rows, _ = await self._execute_raw(
                    "SELECT count() FROM system.columns "
                    "WHERE database = %(database)s AND table = %(table)s AND name = %(name)s"
                    % {
                        "database": quote_clickhouse_string(database),
                        "table": quote_clickhouse_string(table),
                        "name": quote_clickhouse_string(name),
                    }
                )
                exists = bool(rows and int(rows[0][0]))
                self._capability_cache[key] = exists
            if not exists:
                missing.append(f"column {database}.{table}.{name}")
        if missing:
            return False, "missing ClickHouse capability: " + ", ".join(missing)
        return True, None

    async def _catalog_object_exists(self, kind: str, database: str, name: str) -> bool:
        key = (kind, f"{database}.{name}")
        cached = self._capability_cache.get(key)
        if cached is not None:
            return cached
        rows, _ = await self._execute_raw(
            "SELECT count() FROM system.tables "
            f"WHERE database = {quote_clickhouse_string(database)} "
            f"AND name = {quote_clickhouse_string(name)}"
        )
        exists = bool(rows and int(rows[0][0]))
        self._capability_cache[key] = exists
        return exists

    async def resolve_targets(self, scope: str, selector: str | None) -> list[TargetContext]:
        if scope == "node":
            if selector:
                raise ValueError("--cluster-name is only valid with --target-scope cluster")
            return [TargetContext(scope="node")]
        clusters = await self.list_clusters()
        names = [entry["name"] for entry in clusters]
        if not names:
            raise ClickHouseConnectionError(
                "cluster scope requested, but system.clusters contains no clusters"
            )
        value = selector or "AUTO"
        if value == "AUTO":
            return [TargetContext(scope="cluster", cluster_name=names[0])]
        if value == "ALL":
            return [TargetContext(scope="cluster", cluster_name=name) for name in names]
        if value not in names:
            raise ClickHouseConnectionError(
                f"unknown ClickHouse cluster {value!r}; available: {', '.join(names)}"
            )
        return [TargetContext(scope="cluster", cluster_name=value)]

    async def execute_query(
        self,
        sql: str,
        *,
        target: TargetContext,
        timeout_seconds: float | None = None,
        optional_capability: bool = False,
    ) -> dict[str, Any]:
        rendered = render_target_sql(sql, target)
        started = time_module.perf_counter()
        try:
            rows, columns = await self._execute_raw(rendered, timeout_seconds=timeout_seconds)
        except Exception as exc:
            return {
                "collection_status": classify_error(exc, optional_capability=optional_capability),
                "reason": redact_error(exc),
                "timing_ms": round((time_module.perf_counter() - started) * 1000, 3),
                "result": {"kind": "table", "columns": [], "rows": [], "row_count": 0},
                "diagnostics": [
                    {
                        "level": "error",
                        "code": type(exc).__name__,
                        "message": redact_error(exc),
                    }
                ],
                "source_text": rendered,
            }
        public_columns = [column_descriptor(name, ch_type, rows, index) for index, (name, ch_type) in enumerate(columns)]
        public_rows = [
            [json_safe(value, public_columns[index]) for index, value in enumerate(row)]
            for row in rows
        ]
        encoded_size = len(
            json.dumps(public_rows, ensure_ascii=False, allow_nan=False, separators=(",", ":")).encode("utf-8")
        )
        if encoded_size > self.max_result_bytes:
            reason = (
                f"ClickHouse result is {encoded_size} bytes, above limit "
                f"{self.max_result_bytes}"
            )
            return {
                "collection_status": "error",
                "reason": reason,
                "timing_ms": round((time_module.perf_counter() - started) * 1000, 3),
                "result": {"kind": "table", "columns": public_columns, "rows": [], "row_count": 0},
                "diagnostics": [{"level": "error", "code": "result_size_limit", "message": reason}],
                "source_text": rendered,
            }
        return {
            "collection_status": "ok" if public_rows else "empty",
            "reason": None,
            "timing_ms": round((time_module.perf_counter() - started) * 1000, 3),
            "result": {
                "kind": "table",
                "columns": public_columns,
                "rows": public_rows,
                "row_count": len(public_rows),
            },
            "diagnostics": [],
            "source_text": rendered,
        }

    async def _execute_raw(
        self,
        sql: str,
        *,
        timeout_seconds: float | None = None,
    ) -> tuple[list[tuple[Any, ...]], list[tuple[str, str]]]:
        if self._closed:
            raise RuntimeError("ClickHouse adapter is closed")
        timeout = float(timeout_seconds or self.sql_timeout_seconds)
        query_id = "ch_diag_" + uuid4().hex
        client = self._client()
        client_key = id(client)
        with self._clients_lock:
            if self._closed:
                try:
                    client.disconnect()
                finally:
                    raise RuntimeError("ClickHouse adapter is closed")
            self._clients[client_key] = client

        def execute() -> tuple[list[tuple[Any, ...]], list[tuple[str, str]]]:
            try:
                rows, columns = client.execute(
                    sql,
                    with_column_types=True,
                    query_id=query_id,
                    settings=self._settings(timeout),
                )
                return list(rows), list(columns)
            finally:
                try:
                    client.disconnect()
                except Exception:
                    pass
                with self._clients_lock:
                    self._clients.pop(client_key, None)

        loop = asyncio.get_running_loop()
        task = loop.run_in_executor(self._executor, execute)
        try:
            return await asyncio.wait_for(asyncio.shield(task), timeout=timeout)
        except asyncio.TimeoutError as exc:
            try:
                cancel = getattr(client, "cancel", None)
                if callable(cancel):
                    cancel()
                else:
                    client.disconnect()
            except Exception:
                pass
            try:
                await asyncio.wait_for(task, timeout=1.0)
            except BaseException:
                pass
            raise TimeoutError(f"ClickHouse query timed out after {timeout:g}s") from exc

    async def close(self) -> None:
        """Cancel active queries and stop all adapter-owned worker threads."""

        if self._closed:
            return
        self._closed = True
        with self._clients_lock:
            clients = list(self._clients.values())
        for client in clients:
            try:
                cancel = getattr(client, "cancel", None)
                if callable(cancel):
                    cancel()
                else:
                    client.disconnect()
            except Exception:
                try:
                    client.disconnect()
                except Exception:
                    pass

        async def shutdown() -> None:
            await asyncio.to_thread(
                self._executor.shutdown,
                wait=True,
                cancel_futures=True,
            )

        try:
            await asyncio.wait_for(shutdown(), timeout=self.close_timeout_seconds)
        except asyncio.TimeoutError as exc:
            # shutdown(wait=False) is idempotent and prevents queued work from
            # starting.  A driver that ignores socket close remains a driver
            # defect, but it can no longer accept work through this adapter.
            self._executor.shutdown(wait=False, cancel_futures=True)
            raise TimeoutError(
                "ClickHouse workers did not stop within "
                f"{self.close_timeout_seconds:g}s"
            ) from exc


def render_target_sql(sql: str, target: TargetContext) -> str:
    placeholder = "{{cluster}}"
    if target.scope == "node":
        if placeholder in sql:
            raise ValueError("cluster placeholder is not valid in a node query")
        return sql
    if not target.cluster_name:
        raise ValueError("cluster target has no cluster name")
    if placeholder not in sql:
        return sql
    return sql.replace(placeholder, quote_clickhouse_string(target.cluster_name))


def quote_clickhouse_string(value: str) -> str:
    return "'" + value.replace("\\", "\\\\").replace("'", "\\'") + "'"


def _split_qualified_name(value: str, kind: str) -> tuple[str, ...]:
    expected = 2 if kind == "table" else 3
    parts = tuple(value.split("."))
    if len(parts) != expected or any(not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", part) for part in parts):
        raise ValueError(f"invalid required {kind} name {value!r}")
    return parts


def create_clickhouse_adapter(
    config: ConnectionConfig,
    runtime_policy: dict[str, Any],
) -> ClickHouseAdapter:
    """Product factory passed into the neutral collection lifecycle."""

    return ClickHouseAdapter(
        config,
        sql_timeout_seconds=float(runtime_policy.get("default_sql_timeout_seconds", 5.0)),
        max_result_rows=int(runtime_policy.get("max_result_rows", DEFAULT_MAX_RESULT_ROWS)),
        max_result_bytes=int(runtime_policy.get("max_result_bytes", DEFAULT_MAX_RESULT_BYTES)),
        worker_count=int(runtime_policy.get("database_workers", DEFAULT_DATABASE_WORKERS)),
    )


def redact_error(exc: BaseException) -> str:
    text = str(exc).replace("\x00", "")
    text = text.split("Stack trace:", 1)[0].rstrip()
    return _SECRET_RE.sub(lambda match: match.group(1) + match.group(2) + "<redacted>", text)[:4000]


def classify_error(exc: BaseException, *, optional_capability: bool = False) -> str:
    if isinstance(exc, TimeoutError):
        return "timeout"
    text = str(exc).casefold()
    if any(token in text for token in ("not enough privileges", "access denied", "permission denied")):
        return "permission_denied"
    if optional_capability and any(
        token in text
        for token in (
            "doesn't exist",
            "unknown table",
            "unknown identifier",
            "no zookeeper configuration",
            "there is no keeper configuration",
            "no hosts passed to zookeeper constructor",
        )
    ):
        return "unsupported"
    return "error"
