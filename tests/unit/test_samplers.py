from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from types import SimpleNamespace

from ch_diag.content_loader import load_content
from ch_diag.host import CommandResult
from ch_diag.linux_helpers import normalize_iostat_row, parse_iostat_reports
from ch_diag.planner import PlannedItem
from ch_diag.samplers import (
    apply_chart_budget,
    build_chart_result,
    build_table_result,
    chart_coverage_diagnostics,
    clickhouse_thread_pool_rows,
    normalized_clickhouse_process_rows,
    normalized_clickhouse_thread_rows,
    normalized_linux_rows,
    parse_clickhouse_process,
    parse_linux_proc,
)
from ch_diag.snapshots import (
    collect_metric_items,
    iostat_samples,
    iostat_sampling_parameters,
)


PROC_SAMPLE = """__CH_DIAG_STAT__
cpu  100 0 50 500 10 0 5 0 0 0
__CH_DIAG_LOAD__
0.10 0.20 0.30 1/100 1
__CH_DIAG_MEM__
MemTotal:       1000 kB
MemFree:         200 kB
MemAvailable:    400 kB
Buffers:          20 kB
Cached:          100 kB
SwapTotal:       100 kB
SwapFree:         80 kB
__CH_DIAG_NET__
Inter-| Receive | Transmit
 face |bytes packets errs drop fifo frame compressed multicast|bytes packets errs drop fifo colls carrier compressed
  eth0: 1000 10 0 0 0 0 0 0 2000 20 0 0 0 0 0 0
"""

IOSTAT_SAMPLE = """Linux host

Device: r/s w/s rkB/s wkB/s await aqu-sz %util
loop0 0 0 0 0 0 0 0
sda 1 2 3 4 5 6 7

Device: r/s w/s rkB/s wkB/s await aqu-sz %util
loop0 0 0 0 0 0 0 0
sda 10 20 30 40 50 60 70
"""

PROCESS_SAMPLE = """__CH_DIAG_PROCESS_PID__
42
__CH_DIAG_PROCESS_HZ__
100
__CH_DIAG_PROCESS_PAGE_SIZE__
4096
__CH_DIAG_PROCESS_STAT__
42 (clickhouse-serv) S 1 1 1 0 -1 0 0 0 0 0 100 50 0 0 20 0 10 0 1000 2000 25 0 0
__CH_DIAG_PROCESS_IO__
read_bytes: 1000
write_bytes: 2000
__CH_DIAG_PROCESS_THREADS__
101\tS\t500\t10\t5\tQueryPipelineEx
102\tS\t600\t20\t0\tBgSchPool
__CH_DIAG_PROCESS_THREAD_IO__
101\t100\t200
"""


def planned_metric(item_id: str, source_id: str) -> PlannedItem:
    section_id, item_key = item_id.split(".", 1)
    return PlannedItem(
        item_id=item_id,
        section_id=section_id,
        item_key=item_key,
        title=item_key.replace("_", " ").title(),
        source_kind="metric",
        source_id=source_id,
        status="planned",
        state="expanded",
    )


def test_proc_sampler_normalizes_rates_and_memory() -> None:
    previous = parse_linux_proc(PROC_SAMPLE)
    current = parse_linux_proc(
        PROC_SAMPLE.replace("cpu  100 0 50 500 10", "cpu  120 0 60 560 12")
        .replace("eth0: 1000 10", "eth0: 3000 30")
        .replace("2000 20 0", "5000 50 0")
    )
    rows = normalized_linux_rows(previous, current, 2.0)
    assert rows["os.cpu"][0]["util_pct"] > 0
    assert rows["os.network"][0]["rx_bytes_per_sec"] == 1000
    assert rows["os.memory"][0]["total_bytes"] == 1000 * 1024


def test_iostat_parser_accepts_old_and_new_column_names() -> None:
    reports = parse_iostat_reports(
        "Linux host\n\nDevice: r/s w/s rkB/s wkB/s await %util\nsda 1 2 3 4 5 6\n"
    )
    normalized = normalize_iostat_row(reports[0][0])
    assert normalized["read_bytes_per_sec"] == 3 * 1024
    assert normalized["write_iops"] == 2


def test_iostat_samples_use_interval_reports_and_filter_virtual_devices() -> None:
    interval, points = iostat_sampling_parameters(2.0, 1.0)
    samples = iostat_samples(
        IOSTAT_SAMPLE,
        started_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        started_monotonic=10.0,
        duration_seconds=2.0,
        interval_seconds=interval,
        points=points,
    )

    assert interval == 1
    assert points == 2
    assert len(samples) == 2
    assert [[row["device"] for row in sample["rows"]] for sample in samples] == [
        ["sda"],
        ["sda"],
    ]
    assert samples[0]["rows"][0]["read_bytes_per_sec"] == 3 * 1024
    assert samples[1]["rows"][0]["queue_size"] == 60


def test_counter_reset_creates_gap_instead_of_negative_rate() -> None:
    metric = {
        "series": [{"name": "queries", "value_ref": "value", "transform": "rate", "unit": "queries/s"}],
        "chart": {"kind": "line", "unit": "queries/s"},
    }
    result = build_chart_result(
        metric,
        [
            {"timestamp": "2026-01-01T00:00:00Z", "monotonic": 0.0, "rows": [{"value": 10}]},
            {"timestamp": "2026-01-01T00:00:01Z", "monotonic": 1.0, "rows": [{"value": 5}]},
            {"timestamp": "2026-01-01T00:00:02Z", "monotonic": 2.0, "rows": [{"value": 9}]},
        ],
    )
    assert [point["value"] for point in result["series"][0]["points"]] == [None, None, 4.0]


def test_ratio_of_deltas_builds_interval_average_and_ignores_idle_window() -> None:
    metric = {
        "series": [
            {
                "name": "latency",
                "value_ref": "query_time_us",
                "denominator_ref": "queries",
                "transform": "ratio_of_deltas",
                "scale": 0.001,
                "unit": "ms",
            }
        ],
        "chart": {"kind": "line", "unit": "ms"},
    }
    result = build_chart_result(
        metric,
        [
            {
                "timestamp": "2026-01-01T00:00:00Z",
                "monotonic": 0.0,
                "rows": [{"query_time_us": 1000, "queries": 10}],
            },
            {
                "timestamp": "2026-01-01T00:00:01Z",
                "monotonic": 1.0,
                "rows": [{"query_time_us": 7000, "queries": 13}],
            },
            {
                "timestamp": "2026-01-01T00:00:02Z",
                "monotonic": 2.0,
                "rows": [{"query_time_us": 7000, "queries": 13}],
            },
        ],
    )
    assert [point["value"] for point in result["series"][0]["points"]] == [
        None,
        2.0,
        None,
    ]


def test_clickhouse_process_sampler_normalizes_cpu_memory_and_io() -> None:
    previous = parse_clickhouse_process(PROCESS_SAMPLE)
    current = parse_clickhouse_process(
        PROCESS_SAMPLE.replace("100 50 0 0", "200 100 0 0")
        .replace("2000 25", "2000 30")
        .replace("read_bytes: 1000", "read_bytes: 3000")
        .replace("write_bytes: 2000", "write_bytes: 8000")
    )
    row = normalized_clickhouse_process_rows(previous, current, 2.0)[0]
    assert row["pid"] == 42
    assert row["cpu_pct"] == 75.0
    assert row["rss_bytes"] == 30 * 4096
    assert row["read_bytes_per_sec"] == 1000
    assert row["write_bytes_per_sec"] == 3000


def test_clickhouse_process_restart_resets_rates() -> None:
    previous = parse_clickhouse_process(PROCESS_SAMPLE)
    current = {**previous, "pid": 43, "cpu_ticks": 1}
    row = normalized_clickhouse_process_rows(previous, current, 1.0)[0]
    assert row == {"pid": 43, "rss_bytes": previous["rss_bytes"]}


def test_clickhouse_thread_sampler_normalizes_tid_cpu_io_and_pool_names() -> None:
    previous = parse_clickhouse_process(PROCESS_SAMPLE)
    current = parse_clickhouse_process(
        PROCESS_SAMPLE.replace(
            "101\tS\t500\t10\t5",
            "101\tR\t500\t30\t15",
        ).replace(
            "102\tS\t600\t20\t0",
            "102\tS\t600\t30\t0",
        ).replace("101\t100\t200", "101\t1100\t2200")
    )

    rows = normalized_clickhouse_thread_rows(previous, current, 2.0)
    by_tid = {row["tid"]: row for row in rows}
    assert by_tid[101]["thread_name"] == "QueryPipelineEx"
    assert by_tid[101]["state"] == "R"
    assert by_tid[101]["cpu_pct"] == 15.0
    assert by_tid[101]["read_bytes_per_sec"] == 500.0
    assert by_tid[101]["write_bytes_per_sec"] == 1000.0
    assert by_tid[102]["cpu_pct"] == 5.0
    assert "read_bytes_per_sec" not in by_tid[102]

    pools = {row["thread_name"]: row for row in clickhouse_thread_pool_rows(rows)}
    assert pools["QueryPipelineEx"]["thread_count"] == 1
    assert pools["QueryPipelineEx"]["cpu_pct"] == 15.0
    assert pools["BgSchPool"]["io_access_threads"] == 0


def test_snapshot_table_aggregates_and_sorts_thread_samples() -> None:
    metric = {
        "table": {
            "key_refs": ["tid", "starttime"],
            "drop_zero_refs": ["cpu_pct"],
            "sort": {"column": "avg_cpu_pct", "direction": "desc"},
            "limit": 1,
            "columns": [
                {"name": "tid", "role": "key", "key_index": 0, "source_type": "UInt64"},
                {"name": "start", "role": "key", "key_index": 1, "source_type": "UInt64"},
                {"name": "name", "ref": "thread_name", "source_type": "String"},
                {"name": "avg_cpu_pct", "value_ref": "cpu_pct", "transform": "avg", "source_type": "Float64"},
                {"name": "samples", "transform": "sample_count", "source_type": "UInt64"},
            ],
        }
    }
    result = build_table_result(
        metric,
        [
            {"timestamp": "2026-01-01T00:00:01Z", "rows": [
                {"tid": 10, "starttime": 1, "thread_name": "A", "cpu_pct": 5},
                {"tid": 20, "starttime": 2, "thread_name": "B", "cpu_pct": 20},
            ]},
            {"timestamp": "2026-01-01T00:00:02Z", "rows": [
                {"tid": 10, "starttime": 1, "thread_name": "A", "cpu_pct": 15},
                {"tid": 20, "starttime": 2, "thread_name": "B", "cpu_pct": 40},
            ]},
        ],
    )

    assert result["row_count"] == 1
    assert result["rows"][0] == ["20", "2", "B", 30.0, "2"]
    assert result["columns"][3]["quantity"] == "percentage"


def test_mixed_os_and_process_samplers_do_not_duplicate_process_samples() -> None:
    class Adapter:
        async def detect_runtime_context(self) -> dict[str, str]:
            return {"server_version": "25.8"}

    class HostRunner:
        async def run_script(self, script: str, *, timeout: float) -> CommandResult:
            del timeout
            output = PROCESS_SAMPLE if "__CH_DIAG_PROCESS_PID__" in script else PROC_SAMPLE
            return CommandResult(stdout=output, stderr="", returncode=0)

    planned_items = [
        PlannedItem(
            item_id="snapshot_charts_os.os_cpu_utilization",
            section_id="snapshot_charts_os",
            item_key="os_cpu_utilization",
            title="CPU Utilization",
            source_kind="metric",
            source_id="os.cpu_utilization",
            status="planned",
            state="expanded",
        ),
        PlannedItem(
            item_id="snapshot_charts_clickhouse.process_memory",
            section_id="snapshot_charts_clickhouse",
            item_key="process_memory",
            title="ClickHouse Server Process Resident Memory",
            source_kind="metric",
            source_id="clickhouse.process_memory",
            status="planned",
            state="expanded",
        ),
    ]

    items, snapshots, diagnostics = asyncio.run(
        collect_metric_items(
            load_content(),
            Adapter(),
            SimpleNamespace(scope="node"),
            planned_items,
            HostRunner(),
            {"database_host_ip": "127.0.0.1", "database_port": 9000},
            duration_seconds=0.002,
            interval_seconds=0.001,
        )
    )

    process_item = items["snapshot_charts_clickhouse.process_memory"]
    assert len(snapshots) == 3
    assert process_item["result"]["sample_count"] == 3
    assert len(process_item["result"]["series"][0]["points"]) == 3
    assert process_item["result"]["coverage"]["missing_observations"] == 0
    assert not any(entry.get("code") == "series_coverage_gap" for entry in diagnostics)


def test_iostat_failure_does_not_fail_proc_metrics() -> None:
    class Adapter:
        async def detect_runtime_context(self) -> dict[str, str]:
            return {"server_version": "25.8"}

    class HostRunner:
        proc_calls = 0
        iostat_calls = 0

        async def run_script(self, script: str, *, timeout: float) -> CommandResult:
            del timeout
            if "iostat -dxk" in script:
                self.iostat_calls += 1
                return CommandResult(stdout="", stderr="iostat failed", returncode=3)
            self.proc_calls += 1
            return CommandResult(stdout=PROC_SAMPLE, stderr="", returncode=0)

    planned_items = [
        PlannedItem(
            item_id="snapshot_charts_os.os_cpu_utilization",
            section_id="snapshot_charts_os",
            item_key="os_cpu_utilization",
            title="CPU Utilization",
            source_kind="metric",
            source_id="os.cpu_utilization",
            status="planned",
            state="expanded",
        ),
        PlannedItem(
            item_id="snapshot_charts_os.os_disk_read_throughput",
            section_id="snapshot_charts_os",
            item_key="os_disk_read_throughput",
            title="Disk Read Throughput",
            source_kind="metric",
            source_id="os.disk_read_throughput",
            status="planned",
            state="expanded",
        ),
    ]
    host_runner = HostRunner()

    items, _snapshots, _diagnostics = asyncio.run(
        collect_metric_items(
            load_content(),
            Adapter(),
            SimpleNamespace(scope="node"),
            planned_items,
            host_runner,
            {"database_host_ip": "127.0.0.1", "database_port": 9000},
            duration_seconds=0.002,
            interval_seconds=0.001,
        )
    )

    assert host_runner.proc_calls == 3
    assert host_runner.iostat_calls == 1
    assert items["snapshot_charts_os.os_cpu_utilization"]["collection_status"] == "ok"
    disk_item = items["snapshot_charts_os.os_disk_read_throughput"]
    assert disk_item["collection_status"] == "error"
    assert disk_item["reason"] == "iostat failed"


def test_window_end_query_table_executes_once() -> None:
    class Adapter:
        calls = 0

        async def detect_runtime_context(self) -> dict[str, str]:
            return {"server_version": "25.8"}

        async def supports_requirements(self, requirements: object) -> tuple[bool, None]:
            del requirements
            return True, None

        async def execute_query(self, sql: str, **kwargs: object) -> dict[str, object]:
            del sql, kwargs
            self.calls += 1
            names = [
                "host", "event_time", "thread_id", "thread_name", "query_id", "user",
                "query_duration_ms", "cpu_seconds", "cpu_wait_seconds", "os_read_bytes",
                "os_write_bytes", "os_io_bytes", "memory_usage", "peak_memory_usage", "query",
            ]
            return {
                "collection_status": "ok",
                "result": {
                    "columns": [{"name": name} for name in names],
                    "rows": [[
                        "node1", "2026-01-01T00:00:00Z", "101", "QueryPipelineEx",
                        "query-1", "default", "100", 0.5, 0.1, "1000", "2000",
                        "3000", "4096", "8192", "SELECT 1",
                    ]],
                },
            }

    adapter = Adapter()
    planned = PlannedItem(
        item_id="snapshot_charts_clickhouse.logged_thread_cpu_top",
        section_id="snapshot_charts_clickhouse",
        item_key="logged_thread_cpu_top",
        title="Top Logged Query Threads By CPU",
        source_kind="metric",
        source_id="clickhouse.logged_thread_cpu_top",
        status="planned",
        state="collapsed",
    )
    items, snapshots, diagnostics = asyncio.run(
        collect_metric_items(
            load_content(),
            adapter,
            SimpleNamespace(scope="node"),
            [planned],
            None,
            {"database_host_ip": "127.0.0.1", "database_port": 9000},
            duration_seconds=0.002,
            interval_seconds=0.001,
        )
    )

    item = items[planned.item_id]
    assert len(snapshots) == 3
    assert adapter.calls == 1
    assert item["collection_status"] == "ok"
    assert item["result"]["row_count"] == 1
    assert item["result"]["rows"][0][2] == "101"
    assert diagnostics == []


def test_slow_sql_does_not_delay_procfs_schedule() -> None:
    async def scenario() -> tuple[
        dict[str, dict[str, object]],
        list[dict[str, object]],
        list[dict[str, object]],
        int,
    ]:
        host_finished = asyncio.Event()

        class Adapter:
            async def detect_runtime_context(self) -> dict[str, str]:
                return {"server_version": "25.8"}

            async def supports_requirements(self, requirements: object) -> tuple[bool, None]:
                del requirements
                return True, None

            async def execute_query(self, sql: str, **kwargs: object) -> dict[str, object]:
                del sql, kwargs
                await host_finished.wait()
                return {
                    "collection_status": "ok",
                    "result": {
                        "columns": [
                            {"name": "host"},
                            {"name": "queries"},
                            {"name": "selects"},
                            {"name": "failed_queries"},
                        ],
                        "rows": [["node1", 10, 8, 1]],
                    },
                }

        class HostRunner:
            calls = 0

            async def run_script(self, script: str, *, timeout: float) -> CommandResult:
                del script, timeout
                self.calls += 1
                if self.calls == 3:
                    host_finished.set()
                return CommandResult(stdout=PROC_SAMPLE, stderr="", returncode=0)

        host_runner = HostRunner()
        result = await asyncio.wait_for(
            collect_metric_items(
                load_content(),
                Adapter(),
                SimpleNamespace(scope="node"),
                [
                    planned_metric(
                        "snapshot_charts_os.os_cpu_utilization",
                        "os.cpu_utilization",
                    ),
                    planned_metric(
                        "snapshot_charts_clickhouse.query_rate",
                        "clickhouse.query_rate",
                    ),
                ],
                host_runner,
                {"database_host_ip": "127.0.0.1", "database_port": 9000},
                duration_seconds=0.002,
                interval_seconds=0.001,
            ),
            timeout=0.5,
        )
        return *result, host_runner.calls

    items, snapshots, diagnostics, host_calls = asyncio.run(scenario())

    assert host_calls == 3
    assert len(snapshots) == 3
    assert [entry["scheduled_offset_seconds"] for entry in snapshots] == [
        0.0,
        0.001,
        0.002,
    ]
    assert all(
        float(entry["monotonic_offset_seconds"])
        >= float(entry["scheduled_offset_seconds"])
        for entry in snapshots
    )
    assert items["snapshot_charts_os.os_cpu_utilization"]["result"]["sample_count"] == 3
    assert any(
        entry.get("source_id") == "metrics.query_rate"
        and entry.get("code") == "sample_skipped_source_busy"
        for entry in diagnostics
    )


def test_slow_procfs_does_not_delay_process_thread_schedule() -> None:
    async def scenario() -> tuple[
        dict[str, dict[str, object]],
        list[dict[str, object]],
        list[dict[str, object]],
        int,
    ]:
        process_finished = asyncio.Event()

        class Adapter:
            async def detect_runtime_context(self) -> dict[str, str]:
                return {"server_version": "25.8"}

        class HostRunner:
            process_calls = 0

            async def run_script(self, script: str, *, timeout: float) -> CommandResult:
                del timeout
                if "__CH_DIAG_PROCESS_PID__" in script:
                    self.process_calls += 1
                    if self.process_calls == 3:
                        process_finished.set()
                    return CommandResult(stdout=PROCESS_SAMPLE, stderr="", returncode=0)
                await process_finished.wait()
                return CommandResult(stdout=PROC_SAMPLE, stderr="", returncode=0)

        host_runner = HostRunner()
        result = await asyncio.wait_for(
            collect_metric_items(
                load_content(),
                Adapter(),
                SimpleNamespace(scope="node"),
                [
                    planned_metric(
                        "snapshot_charts_os.os_memory_usage",
                        "os.memory_usage",
                    ),
                    planned_metric(
                        "snapshot_charts_clickhouse.process_memory",
                        "clickhouse.process_memory",
                    ),
                ],
                host_runner,
                {"database_host_ip": "127.0.0.1", "database_port": 9000},
                duration_seconds=0.002,
                interval_seconds=0.001,
            ),
            timeout=0.5,
        )
        return *result, host_runner.process_calls

    items, snapshots, diagnostics, process_calls = asyncio.run(scenario())

    assert process_calls == 3
    assert len(snapshots) == 3
    assert items["snapshot_charts_clickhouse.process_memory"]["result"]["sample_count"] == 3
    assert any(
        entry.get("source_id") == "os.memory"
        and entry.get("code") == "sample_skipped_source_busy"
        for entry in diagnostics
    )


def test_slow_source_is_not_overlapped_and_uses_completion_timestamp() -> None:
    async def scenario() -> tuple[
        dict[str, dict[str, object]],
        list[dict[str, object]],
        list[dict[str, object]],
        datetime,
    ]:
        class Adapter:
            async def detect_runtime_context(self) -> dict[str, str]:
                return {"server_version": "25.8"}

        class HostRunner:
            active = 0
            max_active = 0
            completed_at = datetime.min.replace(tzinfo=timezone.utc)

            async def run_script(self, script: str, *, timeout: float) -> CommandResult:
                del script, timeout
                self.active += 1
                self.max_active = max(self.max_active, self.active)
                await asyncio.sleep(0.01)
                self.completed_at = datetime.now(timezone.utc)
                self.active -= 1
                return CommandResult(stdout=PROC_SAMPLE, stderr="", returncode=0)

        host_runner = HostRunner()
        result = await collect_metric_items(
            load_content(),
            Adapter(),
            SimpleNamespace(scope="node"),
            [
                planned_metric(
                    "snapshot_charts_os.os_memory_usage",
                    "os.memory_usage",
                )
            ],
            host_runner,
            {"database_host_ip": "127.0.0.1", "database_port": 9000},
            duration_seconds=0.002,
            interval_seconds=0.001,
        )
        assert host_runner.max_active == 1
        return *result, host_runner.completed_at

    items, _snapshots, diagnostics, completed_at = asyncio.run(scenario())
    point = items["snapshot_charts_os.os_memory_usage"]["result"]["series"][0][
        "points"
    ][0]
    sampled_at = datetime.fromisoformat(str(point["t"]).replace("Z", "+00:00"))

    assert sampled_at >= completed_at
    assert any(
        entry.get("source_id") == "os.memory"
        and entry.get("code") == "sample_skipped_source_busy"
        for entry in diagnostics
    )


def test_snapshot_sql_concurrency_is_bounded_by_database_workers() -> None:
    async def scenario() -> int:
        class Adapter:
            active = 0
            max_active = 0

            async def detect_runtime_context(self) -> dict[str, str]:
                return {"server_version": "25.8"}

            async def supports_requirements(self, requirements: object) -> tuple[bool, None]:
                del requirements
                return True, None

            async def execute_query(self, sql: str, **kwargs: object) -> dict[str, object]:
                del sql, kwargs
                self.active += 1
                self.max_active = max(self.max_active, self.active)
                await asyncio.sleep(0.01)
                self.active -= 1
                return {
                    "collection_status": "empty",
                    "result": {"columns": [], "rows": []},
                }

        content = load_content()
        content.report["runtime_policy"]["database_workers"] = 2
        adapter = Adapter()
        await collect_metric_items(
            content,
            adapter,
            SimpleNamespace(scope="node"),
            [
                planned_metric(
                    "snapshot_charts_clickhouse.query_rate",
                    "clickhouse.query_rate",
                ),
                planned_metric(
                    "snapshot_charts_clickhouse.activity",
                    "clickhouse.activity",
                ),
                planned_metric(
                    "snapshot_charts_clickhouse.replication_queue",
                    "clickhouse.replication_queue",
                ),
            ],
            None,
            {"database_host_ip": "127.0.0.1", "database_port": 9000},
            duration_seconds=0.002,
            interval_seconds=0.001,
        )
        return adapter.max_active

    assert asyncio.run(scenario()) == 2


def test_failing_sql_source_does_not_stop_other_query_sources() -> None:
    class Adapter:
        gauge_calls = 0

        async def detect_runtime_context(self) -> dict[str, str]:
            return {"server_version": "25.8"}

        async def supports_requirements(self, requirements: object) -> tuple[bool, None]:
            del requirements
            return True, None

        async def execute_query(self, sql: str, **kwargs: object) -> dict[str, object]:
            del kwargs
            if "system.events" in sql:
                raise RuntimeError("events source failed")
            self.gauge_calls += 1
            return {
                "collection_status": "ok",
                "result": {
                    "columns": [
                        {"name": "host"},
                        {"name": "current_queries"},
                        {"name": "current_merges"},
                        {"name": "current_mutations"},
                        {"name": "distributed_sends"},
                    ],
                    "rows": [["node1", 1, 2, 3, 4]],
                },
            }

    adapter = Adapter()
    items, snapshots, diagnostics = asyncio.run(
        collect_metric_items(
            load_content(),
            adapter,
            SimpleNamespace(scope="node"),
            [
                planned_metric(
                    "snapshot_charts_clickhouse.query_rate",
                    "clickhouse.query_rate",
                ),
                planned_metric(
                    "snapshot_charts_clickhouse.activity",
                    "clickhouse.activity",
                ),
            ],
            None,
            {"database_host_ip": "127.0.0.1", "database_port": 9000},
            duration_seconds=0.002,
            interval_seconds=0.001,
        )
    )

    assert len(snapshots) == 3
    assert adapter.gauge_calls == 3
    assert items["snapshot_charts_clickhouse.query_rate"]["collection_status"] == "error"
    assert items["snapshot_charts_clickhouse.activity"]["collection_status"] == "ok"
    assert any(
        entry.get("source_id") == "metrics.query_rate"
        and entry.get("code") == "RuntimeError"
        for entry in diagnostics
    )


def test_chart_budget_keeps_latest_points_and_records_truncation() -> None:
    result = {
        "kind": "chart",
        "series_count": 3,
        "series": [
            {
                "name": name,
                "points": [{"t": str(index), "value": index} for index in range(5)],
            }
            for name in ("a", "b", "c")
        ],
    }
    diagnostics = apply_chart_budget(
        result,
        max_series=2,
        max_points_per_series=3,
        max_total_points=5,
    )
    assert result["series_count"] == 2
    assert result["point_count"] == 5
    assert [point["value"] for point in result["series"][0]["points"]] == [2, 3, 4]
    assert [point["value"] for point in result["series"][1]["points"]] == [3, 4]
    assert result["truncation"]["original_point_count"] == 15
    assert diagnostics[0]["code"] == "chart_budget_truncated"


def test_changing_top_n_is_null_padded_and_reported_as_coverage_gap() -> None:
    metric = {
        "partition_by": ["host"],
        "series": [
            {"name": "queries", "value_ref": "value", "transform": "gauge", "unit": "count"}
        ],
        "chart": {"kind": "line", "unit": "count"},
    }
    result = build_chart_result(
        metric,
        [
            {
                "timestamp": "2026-01-01T00:00:00Z",
                "monotonic": 0.0,
                "rows": [{"host": "node1", "value": 1}],
            },
            {
                "timestamp": "2026-01-01T00:00:01Z",
                "monotonic": 1.0,
                "rows": [{"host": "node2", "value": 2}],
            },
            {
                "timestamp": "2026-01-01T00:00:02Z",
                "monotonic": 2.0,
                "rows": [
                    {"host": "node1", "value": 3},
                    {"host": "node2", "value": 4},
                ],
            },
        ],
    )
    by_name = {series["name"]: series for series in result["series"]}
    assert [point["value"] for point in by_name["queries (node1)"]["points"]] == [1, None, 3]
    assert [point["value"] for point in by_name["queries (node2)"]["points"]] == [None, 2, 4]
    assert result["coverage"] == {
        "effective_sample_count": 3,
        "observed_series_count": 2,
        "missing_observations": 2,
        "topology_changes": 2,
    }
    assert chart_coverage_diagnostics(result)[0]["code"] == "series_coverage_gap"
