from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from ch_diag.clickhouse import ConnectionConfig
from ch_diag.cli import _collection_exit_status
from ch_diag.collector import _close_collection_resources, collect_one_shot
from ch_diag.content_loader import load_content
from ch_diag.database_adapter import DatabaseTarget
from ch_diag.errors import ChDiagError
from ch_diag.artifact_schema import column_descriptor


class _Adapter:
    def __init__(self) -> None:
        self.query_calls = 0
        self.closed = False

    async def detect_runtime_context(self) -> dict[str, object]:
        return {
            "server_version": "25.8",
            "current_database": "default",
            "current_user": "diagnostic",
            "database_hostname": "clickhouse-1",
        }

    async def resolve_targets(
        self,
        scope: str,
        selector: str | None,
    ) -> list[DatabaseTarget]:
        del selector
        return [DatabaseTarget(scope=scope)]

    async def supports_requirements(
        self,
        requirements: dict[str, object] | None,
    ) -> tuple[bool, None]:
        del requirements
        return True, None

    async def execute_query(self, sql: str, **kwargs: object) -> dict[str, object]:
        del sql, kwargs
        self.query_calls += 1
        if self.query_calls == 1:
            raise RuntimeError("first item failed")
        return {
            "collection_status": "empty",
            "result": {"kind": "table", "columns": [], "rows": [], "row_count": 0},
            "diagnostics": [],
        }

    async def close(self) -> None:
        self.closed = True


def test_item_exception_is_recorded_and_independent_collection_continues(
    tmp_path: Path,
) -> None:
    adapter = _Adapter()
    artifacts = asyncio.run(
        collect_one_shot(
            load_content(),
            ConnectionConfig(),
            out_dir=tmp_path,
            collection_mode="remote-db-only",
            target_scope="node",
            item_ids=["overview.server", "overview.clusters"],
            output_formats=("json",),
            adapter_factory=lambda _connection, _policy: adapter,
        )
    )

    artifact = artifacts[0]
    assert artifact["items"]["overview.server"]["collection_status"] == "error"
    assert artifact["items"]["overview.clusters"]["collection_status"] == "empty"
    assert artifact["runtime"]["completion_status"] == "partial"
    assert artifact["runtime"]["collection_summary"] == {
        "total_items": 2,
        "successful_items": 1,
        "complete_items": 1,
        "failed_items": 1,
        "coverage_incomplete_items": 0,
        "completeness_ratio": 0.5,
    }
    assert adapter.query_calls == 2
    assert adapter.closed is True
    assert (tmp_path / "report.json").is_file()


def test_fail_fast_stops_after_first_failed_item(tmp_path: Path) -> None:
    content = load_content()
    content.report["runtime_policy"]["fail_fast"] = True
    adapter = _Adapter()

    with pytest.raises(ChDiagError, match="fail_fast stopped collection"):
        asyncio.run(
            collect_one_shot(
                content,
                ConnectionConfig(),
                out_dir=tmp_path,
                collection_mode="remote-db-only",
                target_scope="node",
                item_ids=["overview.server", "overview.clusters"],
                output_formats=("json",),
                adapter_factory=lambda _connection, _policy: adapter,
            )
        )

    assert adapter.query_calls == 1
    assert adapter.closed is True
    assert not (tmp_path / "report.json").exists()


def test_collection_exit_status_rejects_timeout_or_incomplete_coverage() -> None:
    assert _collection_exit_status(
        [{"runtime": {}, "items": {"item": {"collection_status": "timeout"}}}]
    ) == 1
    assert _collection_exit_status(
        [{"runtime": {"completion_status": "partial"}, "items": {}}]
    ) == 1
    assert _collection_exit_status(
        [{"runtime": {"completion_status": "succeeded"}, "items": {}}]
    ) == 0


def test_declared_fallback_replaces_failed_primary_and_marks_report_degraded(
    tmp_path: Path,
) -> None:
    content = load_content()
    content.report["fallback_items"] = {
        "fallback.overview.server": {
            "title": "Fallback server query",
            "query": "overview.clusters",
        }
    }
    content.report["sections"]["overview"]["items"]["server"].update(
        {
            "fallback_item": "fallback.overview.server",
            "fallback_on": ["query_timeout"],
        }
    )

    class FallbackAdapter(_Adapter):
        async def execute_query(self, sql: str, **kwargs: object) -> dict[str, object]:
            del sql, kwargs
            self.query_calls += 1
            if self.query_calls == 1:
                return {
                    "collection_status": "timeout",
                    "reason": "primary timed out",
                    "timing_ms": 10.0,
                    "result": {"kind": "table", "columns": [], "rows": [], "row_count": 0},
                    "diagnostics": [
                        {
                            "level": "error",
                            "code": "TimeoutError",
                            "failure_kind": "query_timeout",
                            "message": "primary timed out",
                        }
                    ],
                }
            return {
                "collection_status": "empty",
                "timing_ms": 2.0,
                "result": {"kind": "table", "columns": [], "rows": [], "row_count": 0},
                "diagnostics": [],
            }

    adapter = FallbackAdapter()
    artifact = asyncio.run(
        collect_one_shot(
            content,
            ConnectionConfig(),
            out_dir=tmp_path,
            collection_mode="remote-db-only",
            target_scope="node",
            item_ids=["overview.server"],
            output_formats=("json",),
            adapter_factory=lambda _connection, _policy: adapter,
        )
    )[0]
    item = artifact["items"]["overview.server"]
    assert item["collection_status"] == "empty"
    assert item["source_metadata"]["fallback"]["used"] is True
    assert item["source_metadata"]["fallback"]["primary_diagnostics"][0][
        "failure_kind"
    ] == "query_timeout"
    assert item["diagnostics"][0]["code"] == "fallback_item_activated"
    assert artifact["runtime"]["collection_summary"]["fallback_items"] == 1
    assert artifact["runtime"]["degraded"] is True


def test_filtered_local_host_item_does_not_create_database_adapter(tmp_path: Path) -> None:
    def unexpected_factory(*_args: object):
        raise AssertionError("database adapter must not be created")

    artifact = asyncio.run(
        collect_one_shot(
            load_content(),
            ConnectionConfig(),
            out_dir=tmp_path,
            collection_mode="local",
            target_scope="node",
            item_ids=["operating_system.kernel_version"],
            output_formats=("json",),
            adapter_factory=unexpected_factory,
        )
    )[0]
    assert artifact["runtime"]["database_connected"] is False
    assert artifact["runtime"]["targets"] == ["host"]
    assert artifact["items"]["operating_system.kernel_version"]["collection_status"] == "ok"


def test_database_and_ssh_cleanup_are_independent() -> None:
    class Resource:
        def __init__(self, error: BaseException | None = None) -> None:
            self.error = error
            self.closed = False

        async def close(self) -> None:
            self.closed = True
            if self.error is not None:
                raise self.error

    adapter = Resource(RuntimeError("adapter close failed"))
    ssh = Resource()
    with pytest.raises(RuntimeError, match="adapter close failed"):
        asyncio.run(
            _close_collection_resources(adapter, ssh, suppress_errors=False)  # type: ignore[arg-type]
        )
    assert adapter.closed is True
    assert ssh.closed is True

    adapter = Resource(RuntimeError("adapter close failed"))
    ssh = Resource(RuntimeError("ssh close failed"))
    asyncio.run(
        _close_collection_resources(adapter, ssh, suppress_errors=True)  # type: ignore[arg-type]
    )
    assert adapter.closed is True
    assert ssh.closed is True


def test_declared_result_limit_marks_successful_item_coverage_partial(
    tmp_path: Path,
) -> None:
    class LimitedAdapter(_Adapter):
        async def execute_query(self, sql: str, **kwargs: object) -> dict[str, object]:
            del sql, kwargs
            rows = [[value] for value in range(30)]
            columns = [column_descriptor("value", "UInt64", rows, 0)]
            return {
                "collection_status": "ok",
                "result": {
                    "kind": "table",
                    "columns": columns,
                    "rows": rows,
                    "row_count": len(rows),
                },
                "diagnostics": [],
            }

    artifact = asyncio.run(
        collect_one_shot(
            load_content(),
            ConnectionConfig(),
            out_dir=tmp_path,
            collection_mode="remote-db-only",
            target_scope="node",
            item_ids=["query_workload.queries_top_long"],
            output_formats=("json",),
            adapter_factory=lambda _connection, _policy: LimitedAdapter(),
        )
    )[0]

    item = artifact["items"]["query_workload.queries_top_long"]
    assert item["collection_status"] == "ok"
    assert item["diagnostics"][-1]["code"] == "declared_result_limit_reached"
    assert item["diagnostics"][-1]["coverage_incomplete"] is True
    assert artifact["runtime"]["completion_status"] == "partial"
