"""Autonomous Linux sampler and chart metric transformations."""

from __future__ import annotations

from datetime import datetime, timezone
import math
import re
from typing import Any

from .linux_helpers import _cpu_row, _memory_row_from_values, _network_rows


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def parse_linux_proc(output: str) -> dict[str, Any]:
    sections: dict[str, list[str]] = {}
    current = ""
    for line in output.splitlines():
        if line.startswith("__CH_DIAG_") and line.endswith("__"):
            current = line
            sections[current] = []
        elif current:
            sections[current].append(line)

    stat_parts = (sections.get("__CH_DIAG_STAT__") or [""])[0].split()
    if not stat_parts or stat_parts[0] != "cpu":
        raise ValueError("host /proc/stat output is missing the aggregate CPU row")
    cpu_keys = [
        "user", "nice", "system", "idle", "iowait", "irq", "softirq", "steal",
        "guest", "guest_nice",
    ]
    cpu_values = [int(value) for value in stat_parts[1:]]
    cpu = {
        key: cpu_values[index] if index < len(cpu_values) else 0
        for index, key in enumerate(cpu_keys)
    }

    load_parts = (sections.get("__CH_DIAG_LOAD__") or [""])[0].split()
    if len(load_parts) < 3:
        raise ValueError("host /proc/loadavg output is incomplete")
    load = {"load1": float(load_parts[0]), "load5": float(load_parts[1]), "load15": float(load_parts[2])}

    memory: dict[str, int] = {}
    for line in sections.get("__CH_DIAG_MEM__") or []:
        if ":" not in line:
            continue
        key, raw_value = line.split(":", 1)
        parts = raw_value.strip().split()
        if parts:
            multiplier = 1024 if len(parts) > 1 and parts[1].casefold() == "kb" else 1
            memory[key] = int(parts[0]) * multiplier

    network: dict[str, dict[str, int]] = {}
    for line in (sections.get("__CH_DIAG_NET__") or [])[2:]:
        if ":" not in line:
            continue
        name, raw_values = line.split(":", 1)
        interface = name.strip()
        values = raw_values.split()
        if interface == "lo" or len(values) < 16:
            continue
        network[interface] = {
            "rx_bytes": int(values[0]),
            "rx_packets": int(values[1]),
            "tx_bytes": int(values[8]),
            "tx_packets": int(values[9]),
        }

    disks: dict[str, dict[str, int]] = {}
    for line in sections.get("__CH_DIAG_DISK__") or []:
        fields = line.split()
        if len(fields) < 14:
            continue
        device = fields[2]
        if re.match(r"^(loop|ram|zram|fd)\d+", device):
            continue
        disks[device] = {
            "read_ios": int(fields[3]),
            "read_sectors": int(fields[5]),
            "read_ms": int(fields[6]),
            "write_ios": int(fields[7]),
            "write_sectors": int(fields[9]),
            "write_ms": int(fields[10]),
            "io_ms": int(fields[12]),
        }
    return {"cpu": cpu, "load": load, "memory": memory, "network": network, "disk": disks}


def normalized_linux_rows(
    previous: dict[str, Any] | None,
    current: dict[str, Any],
    elapsed: float | None,
) -> dict[str, list[dict[str, Any]]]:
    memory_row = _memory_row_from_values(current["memory"])
    memory_row.update(current["load"])
    outputs: dict[str, list[dict[str, Any]]] = {
        "os.memory": [memory_row],
        "os.cpu": [],
        "os.network": [],
        "os.disk": [],
    }
    if previous is None or elapsed is None:
        return outputs
    seconds = max(float(elapsed), 0.001)
    cpu_row = _cpu_row(previous["cpu"], current["cpu"], seconds)
    cpu_row.update(current["load"])
    outputs["os.cpu"] = [cpu_row]
    outputs["os.network"] = _network_rows(previous["network"], current["network"], seconds)
    outputs["os.disk"] = _disk_rows(previous["disk"], current["disk"], seconds)
    return outputs


def parse_clickhouse_process(output: str) -> dict[str, Any]:
    sections: dict[str, list[str]] = {}
    current = ""
    for line in output.splitlines():
        if line.startswith("__CH_DIAG_PROCESS_") and line.endswith("__"):
            current = line
            sections[current] = []
        elif current:
            sections[current].append(line)
    try:
        pid = int(sections["__CH_DIAG_PROCESS_PID__"][0])
        hz = int(sections["__CH_DIAG_PROCESS_HZ__"][0])
        page_size = int(sections["__CH_DIAG_PROCESS_PAGE_SIZE__"][0])
        stat = sections["__CH_DIAG_PROCESS_STAT__"][0]
    except (KeyError, IndexError, ValueError) as exc:
        raise ValueError("ClickHouse process sampler output is incomplete") from exc
    closing_parenthesis = stat.rfind(")")
    if closing_parenthesis < 0:
        raise ValueError("ClickHouse /proc stat row is malformed")
    fields = stat[closing_parenthesis + 2 :].split()
    if len(fields) < 22:
        raise ValueError("ClickHouse /proc stat row is incomplete")
    io: dict[str, int] = {}
    for line in sections.get("__CH_DIAG_PROCESS_IO__") or []:
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        try:
            io[key.strip()] = int(value.strip())
        except ValueError:
            continue
    return {
        "pid": pid,
        "hz": hz,
        "cpu_ticks": int(fields[11]) + int(fields[12]),
        "rss_bytes": max(int(fields[21]), 0) * page_size,
        "read_bytes": io.get("read_bytes"),
        "write_bytes": io.get("write_bytes"),
    }


def normalized_clickhouse_process_rows(
    previous: dict[str, Any] | None,
    current: dict[str, Any],
    elapsed: float | None,
) -> list[dict[str, Any]]:
    row: dict[str, Any] = {
        "pid": current["pid"],
        "rss_bytes": current["rss_bytes"],
    }
    if (
        previous is None
        or elapsed is None
        or previous.get("pid") != current.get("pid")
    ):
        return [row]
    seconds = max(float(elapsed), 0.001)
    tick_delta = _counter_delta(previous["cpu_ticks"], current["cpu_ticks"])
    if tick_delta is not None:
        row["cpu_pct"] = tick_delta / max(int(current["hz"]), 1) / seconds * 100.0
    for key in ("read_bytes", "write_bytes"):
        old = previous.get(key)
        new = current.get(key)
        if old is None or new is None:
            continue
        delta = _counter_delta(int(old), int(new))
        if delta is not None:
            row[key + "_per_sec"] = delta / seconds
    return [row]


def _disk_rows(
    previous: dict[str, dict[str, int]],
    current: dict[str, dict[str, int]],
    seconds: float,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for device in sorted(current):
        old = previous.get(device)
        new = current[device]
        if old is None:
            continue
        read_ios = _counter_delta(old["read_ios"], new["read_ios"])
        write_ios = _counter_delta(old["write_ios"], new["write_ios"])
        read_ms = _counter_delta(old["read_ms"], new["read_ms"])
        write_ms = _counter_delta(old["write_ms"], new["write_ms"])
        io_ms = _counter_delta(old["io_ms"], new["io_ms"])
        read_sectors = _counter_delta(old["read_sectors"], new["read_sectors"])
        write_sectors = _counter_delta(old["write_sectors"], new["write_sectors"])
        if None in (read_ios, write_ios, read_ms, write_ms, io_ms, read_sectors, write_sectors):
            continue
        total_ios = int(read_ios) + int(write_ios)
        rows.append(
            {
                "device": device,
                "read_bytes_per_sec": int(read_sectors) * 512 / seconds,
                "write_bytes_per_sec": int(write_sectors) * 512 / seconds,
                "read_iops": int(read_ios) / seconds,
                "write_iops": int(write_ios) / seconds,
                "util_pct": min(int(io_ms) / (seconds * 10.0), 100.0),
                "await_ms": (int(read_ms) + int(write_ms)) / total_ios if total_ios else 0.0,
                "r_await_ms": int(read_ms) / int(read_ios) if read_ios else 0.0,
                "w_await_ms": int(write_ms) / int(write_ios) if write_ios else 0.0,
            }
        )
    return rows


def _counter_delta(previous: int, current: int) -> int | None:
    return current - previous if current >= previous else None


def build_chart_result(metric: dict[str, Any], samples: list[dict[str, Any]]) -> dict[str, Any]:
    partition_by = [str(value) for value in metric.get("partition_by") or []]
    series_specs = list(metric.get("series") or [])
    grouped: dict[tuple[str, tuple[str, ...]], dict[str, Any]] = {}
    previous: dict[tuple[int, tuple[str, ...]], tuple[float, float]] = {}
    timeline = [str(sample["timestamp"]) for sample in samples]
    active_by_sample: list[set[tuple[str, tuple[str, ...]]]] = [set() for _ in samples]

    for sample_index, sample in enumerate(samples):
        timestamp = str(sample["timestamp"])
        monotonic = float(sample["monotonic"])
        for row in sample.get("rows") or []:
            dimensions = tuple(str(_nested(row, key) or "") for key in partition_by)
            for index, spec in enumerate(series_specs):
                raw = _nested(row, str(spec.get("value_ref") or ""))
                numeric = _number(raw)
                if numeric is None:
                    continue
                transform = str(spec.get("transform") or "gauge")
                value: float | None = numeric
                previous_key = (index, dimensions)
                if transform in {"rate", "delta"}:
                    old = previous.get(previous_key)
                    previous[previous_key] = (numeric, monotonic)
                    if old is None or numeric < old[0]:
                        value = None
                    else:
                        delta = numeric - old[0]
                        value = delta / max(monotonic - old[1], 0.001) if transform == "rate" else delta
                name = str(spec.get("name") or spec.get("name_from_ref") or spec.get("value_ref") or "series")
                if spec.get("name_from_ref"):
                    name = str(_nested(row, str(spec["name_from_ref"])) or name)
                if dimensions:
                    label = ", ".join(value for value in dimensions if value)
                    if label:
                        name = f"{name} ({label})"
                key = (name, dimensions)
                active_by_sample[sample_index].add(key)
                entry = grouped.setdefault(
                    key,
                    {
                        "name": name,
                        "unit": str(spec.get("unit") or (metric.get("chart") or {}).get("unit") or "count"),
                        "color": spec.get("color"),
                        "points": [],
                    },
                )
                entry["points"].append({"t": timestamp, "value": value})

    result_series = []
    for entry in grouped.values():
        points_by_time = {str(point["t"]): point["value"] for point in entry["points"]}
        entry["points"] = [
            {"t": timestamp, "value": points_by_time.get(timestamp)}
            for timestamp in timeline
        ]
        if any(point["value"] is not None for point in entry["points"]):
            result_series.append(entry)

    first_active = next(
        (index for index, active in enumerate(active_by_sample) if active),
        len(active_by_sample),
    )
    effective_active = active_by_sample[first_active:]
    all_keys = set().union(*effective_active) if effective_active else set()
    missing_observations = sum(len(all_keys - active) for active in effective_active)
    topology_changes = sum(
        active != previous_active
        for previous_active, active in zip(effective_active, effective_active[1:])
    )
    return {
        "kind": "chart",
        "chart": {"x_type": "datetime", **dict(metric.get("chart") or {})},
        "sample_count": len(samples),
        "series_count": len(result_series),
        "series": result_series,
        "coverage": {
            "effective_sample_count": len(effective_active),
            "observed_series_count": len(all_keys),
            "missing_observations": missing_observations,
            "topology_changes": topology_changes,
        },
    }


def chart_coverage_diagnostics(result: dict[str, Any]) -> list[dict[str, str]]:
    coverage = result.get("coverage") or {}
    missing = int(coverage.get("missing_observations") or 0)
    changes = int(coverage.get("topology_changes") or 0)
    if not missing and not changes:
        return []
    return [
        {
            "level": "warning",
            "code": "series_coverage_gap",
            "message": (
                f"chart series coverage has {missing} missing observation(s) and "
                f"{changes} topology/top-N change(s); gaps are rendered as null"
            ),
        }
    ]


def apply_chart_budget(
    result: dict[str, Any],
    *,
    max_series: int,
    max_points_per_series: int,
    max_total_points: int,
) -> list[dict[str, str]]:
    """Bound a chart deterministically, retaining the newest sampled points."""

    if min(max_series, max_points_per_series, max_total_points) < 1:
        raise ValueError("chart budgets must be positive")
    original_series = list(result.get("series") or [])
    original_series_count = len(original_series)
    original_point_count = sum(len(series.get("points") or []) for series in original_series)
    retained = original_series[:max_series]
    for series in retained:
        points = list(series.get("points") or [])
        if len(points) > max_points_per_series:
            series["points"] = points[-max_points_per_series:]

    remaining = max_total_points
    bounded: list[dict[str, Any]] = []
    for series in retained:
        if remaining <= 0:
            break
        points = list(series.get("points") or [])
        if len(points) > remaining:
            series["points"] = points[-remaining:]
        remaining -= len(series.get("points") or [])
        if series.get("points"):
            bounded.append(series)
    result["series"] = bounded
    result["series_count"] = len(bounded)
    retained_point_count = sum(len(series.get("points") or []) for series in bounded)
    result["point_count"] = retained_point_count
    if len(bounded) == original_series_count and retained_point_count == original_point_count:
        return []
    result["truncated"] = True
    result["truncation"] = {
        "original_series_count": original_series_count,
        "retained_series_count": len(bounded),
        "original_point_count": original_point_count,
        "retained_point_count": retained_point_count,
        "max_series": max_series,
        "max_points_per_series": max_points_per_series,
        "max_total_points": max_total_points,
    }
    return [
        {
            "level": "warning",
            "code": "chart_budget_truncated",
            "message": (
                "chart data truncated from "
                f"{original_series_count} series/{original_point_count} points to "
                f"{len(bounded)} series/{retained_point_count} points"
            ),
        }
    ]


def _nested(row: dict[str, Any], path: str) -> Any:
    value: Any = row
    for part in path.split("."):
        if not isinstance(value, dict):
            return None
        value = value.get(part)
    return value


def _number(value: Any) -> float | None:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None
