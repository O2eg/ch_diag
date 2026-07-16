from __future__ import annotations

from ch_diag.linux_helpers import normalize_iostat_row, parse_iostat_reports
from ch_diag.samplers import (
    apply_chart_budget,
    build_chart_result,
    chart_coverage_diagnostics,
    normalized_clickhouse_process_rows,
    normalized_linux_rows,
    parse_clickhouse_process,
    parse_linux_proc,
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
__CH_DIAG_DISK__
8 0 sda 10 0 100 20 20 0 200 40 0 50 0 0 0 0 0
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
"""


def test_proc_sampler_normalizes_rates_and_memory() -> None:
    previous = parse_linux_proc(PROC_SAMPLE)
    current = parse_linux_proc(
        PROC_SAMPLE.replace("cpu  100 0 50 500 10", "cpu  120 0 60 560 12")
        .replace("eth0: 1000 10", "eth0: 3000 30")
        .replace("2000 20 0", "5000 50 0")
        .replace("8 0 sda 10 0 100 20 20 0 200 40 0 50", "8 0 sda 12 0 120 24 23 0 240 46 0 60")
    )
    rows = normalized_linux_rows(previous, current, 2.0)
    assert rows["os.cpu"][0]["util_pct"] > 0
    assert rows["os.network"][0]["rx_bytes_per_sec"] == 1000
    assert rows["os.disk"][0]["read_bytes_per_sec"] == 5120
    assert rows["os.memory"][0]["total_bytes"] == 1000 * 1024


def test_iostat_parser_accepts_old_and_new_column_names() -> None:
    reports = parse_iostat_reports(
        "Linux host\n\nDevice: r/s w/s rkB/s wkB/s await %util\nsda 1 2 3 4 5 6\n"
    )
    normalized = normalize_iostat_row(reports[0][0])
    assert normalized["read_bytes_per_sec"] == 3 * 1024
    assert normalized["write_iops"] == 2


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
