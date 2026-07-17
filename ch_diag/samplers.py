"""Autonomous Linux sampler and chart metric transformations."""

from __future__ import annotations

from datetime import datetime, timezone
import math
from typing import Any

from .artifact_schema import column_descriptor
from .linux_helpers import _cpu_row, _memory_row_from_values, _network_rows
from .serialization import json_safe


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

    return {"cpu": cpu, "load": load, "memory": memory, "network": network}


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
    }
    if previous is None or elapsed is None:
        return outputs
    seconds = max(float(elapsed), 0.001)
    cpu_row = _cpu_row(previous["cpu"], current["cpu"], seconds)
    cpu_row.update(current["load"])
    outputs["os.cpu"] = [cpu_row]
    outputs["os.network"] = _network_rows(previous["network"], current["network"], seconds)
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
    thread_io: dict[int, tuple[int, int]] = {}
    for line in sections.get("__CH_DIAG_PROCESS_THREAD_IO__") or []:
        parts = line.split("\t")
        if len(parts) != 3:
            continue
        try:
            thread_io[int(parts[0])] = (int(parts[1]), int(parts[2]))
        except ValueError:
            continue
    threads: dict[int, dict[str, Any]] = {}
    for line in sections.get("__CH_DIAG_PROCESS_THREADS__") or []:
        parts = line.split("\t", 5)
        if len(parts) != 6:
            continue
        try:
            thread_id = int(parts[0])
        except ValueError:
            continue
        io_values = thread_io.get(thread_id)
        try:
            threads[thread_id] = {
                "tid": thread_id,
                "state": parts[1],
                "starttime": int(parts[2]),
                "cpu_ticks": int(parts[3]) + int(parts[4]),
                "read_bytes": io_values[0] if io_values is not None else 0,
                "write_bytes": io_values[1] if io_values is not None else 0,
                "io_access": io_values is not None,
                "thread_name": parts[5],
            }
        except ValueError:
            continue
    return {
        "pid": pid,
        "hz": hz,
        "cpu_ticks": int(fields[11]) + int(fields[12]),
        "rss_bytes": max(int(fields[21]), 0) * page_size,
        "read_bytes": io.get("read_bytes"),
        "write_bytes": io.get("write_bytes"),
        "threads": threads,
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


def normalized_clickhouse_thread_rows(
    previous: dict[str, Any] | None,
    current: dict[str, Any],
    elapsed: float | None,
) -> list[dict[str, Any]]:
    """Return interval CPU and I/O rates for stable ClickHouse Linux TIDs."""

    previous_threads = (previous or {}).get("threads") or {}
    current_threads = current.get("threads") or {}
    same_process = previous is not None and previous.get("pid") == current.get("pid")
    seconds = max(float(elapsed or 0.0), 0.001)
    rows: list[dict[str, Any]] = []
    for tid in sorted(current_threads):
        thread = current_threads[tid]
        row: dict[str, Any] = {
            "pid": current["pid"],
            "tid": tid,
            "thread_name": thread.get("thread_name") or "",
            "state": thread.get("state") or "",
            "starttime": thread.get("starttime"),
            "io_access": bool(thread.get("io_access")),
        }
        old = previous_threads.get(tid) if same_process else None
        if (
            old is not None
            and elapsed is not None
            and old.get("starttime") == thread.get("starttime")
        ):
            tick_delta = _counter_delta(
                int(old.get("cpu_ticks") or 0),
                int(thread.get("cpu_ticks") or 0),
            )
            if tick_delta is not None:
                row["cpu_pct"] = (
                    tick_delta / max(int(current.get("hz") or 0), 1) / seconds * 100.0
                )
            if old.get("io_access") and thread.get("io_access"):
                for key in ("read_bytes", "write_bytes"):
                    delta = _counter_delta(
                        int(old.get(key) or 0),
                        int(thread.get(key) or 0),
                    )
                    if delta is not None:
                        row[key + "_per_sec"] = delta / seconds
        rows.append(row)
    return rows


def clickhouse_thread_pool_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Aggregate one normalized TID sample by ClickHouse/Linux thread name."""

    pools: dict[str, dict[str, Any]] = {}
    for row in rows:
        name = str(row.get("thread_name") or "<unnamed>")
        pool = pools.setdefault(
            name,
            {
                "thread_name": name,
                "thread_count": 0,
                "io_access_threads": 0,
            },
        )
        pool["thread_count"] += 1
        if row.get("io_access"):
            pool["io_access_threads"] += 1
        for key in ("cpu_pct", "read_bytes_per_sec", "write_bytes_per_sec"):
            value = _number(row.get(key))
            if value is not None:
                pool[key] = float(pool.get(key) or 0.0) + value
    return [pools[name] for name in sorted(pools, key=str.casefold)]


def _counter_delta(previous: int, current: int) -> int | None:
    return current - previous if current >= previous else None


def build_table_result(metric: dict[str, Any], samples: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate repeated sampler/query rows into a bounded snapshot table."""

    table = dict(metric.get("table") or {})
    column_specs = list(table.get("columns") or [])
    key_refs = [str(value) for value in table.get("key_refs") or []]
    groups: dict[tuple[Any, ...], dict[str, Any]] = {}
    sorted_samples = sorted(samples, key=lambda sample: str(sample.get("timestamp") or ""))
    for sample_index, sample in enumerate(sorted_samples):
        for row in sample.get("rows") or []:
            key = tuple(_nested(row, ref) for ref in key_refs)
            if not key_refs:
                key = (len(groups),)
            group = groups.setdefault(key, {"rows": [], "last": row, "samples": set()})
            group["rows"].append(row)
            group["last"] = row
            group["samples"].add(sample_index)

    columns: list[dict[str, Any]] = []
    for index, spec in enumerate(column_specs):
        name = str(spec.get("name") or spec.get("ref") or "value")
        descriptor = column_descriptor(name, str(spec.get("source_type") or "String"), [], index)
        for key in (
            "label",
            "semantic_role",
            "quantity",
            "unit",
            "quality",
            "nullable",
        ):
            if key in spec:
                descriptor[key] = spec[key]
        columns.append(descriptor)

    rendered: list[tuple[list[Any], dict[str, Any]]] = []
    drop_zero_refs = [str(value) for value in table.get("drop_zero_refs") or []]
    for key, group in groups.items():
        if drop_zero_refs and not any(
            (_number(_nested(row, ref)) or 0.0) != 0.0
            for row in group["rows"]
            for ref in drop_zero_refs
        ):
            continue
        values: list[Any] = []
        for spec in column_specs:
            if spec.get("role") == "key":
                key_index = int(spec.get("key_index") or 0)
                value = key[key_index] if key_index < len(key) else None
            else:
                ref = str(spec.get("value_ref") or spec.get("ref") or "")
                transform = str(spec.get("transform") or "last")
                raw_values = [_nested(row, ref) for row in group["rows"]] if ref else []
                numeric = [value for raw in raw_values if (value := _number(raw)) is not None]
                if transform == "avg":
                    value = sum(numeric) / len(numeric) if numeric else None
                elif transform == "max":
                    value = max(numeric) if numeric else None
                elif transform == "sum":
                    value = sum(numeric) if numeric else None
                elif transform == "sample_count":
                    value = len(group["samples"])
                else:
                    value = _nested(group["last"], ref) if ref else None
            values.append(value)
        rendered.append((values, group))

    sort = dict(table.get("sort") or {})
    sort_name = str(sort.get("column") or "")
    sort_index = next(
        (index for index, column in enumerate(columns) if column["name"] == sort_name),
        None,
    )
    if sort_index is not None:
        descending = str(sort.get("direction") or "asc") == "desc"

        def sort_key(entry: tuple[list[Any], dict[str, Any]]) -> tuple[int, float | str]:
            value = entry[0][sort_index]
            numeric = _number(value)
            if numeric is not None:
                return 0, numeric
            return 1, str(value or "").casefold()

        present = [entry for entry in rendered if entry[0][sort_index] is not None]
        missing = [entry for entry in rendered if entry[0][sort_index] is None]
        present.sort(key=sort_key, reverse=descending)
        rendered = present + missing
    limit = table.get("limit")
    if isinstance(limit, int) and limit > 0:
        rendered = rendered[:limit]
    public_rows = [
        [json_safe(value, columns[index]) for index, value in enumerate(values)]
        for values, _group in rendered
    ]
    result = {
        "kind": "table",
        "columns": columns,
        "rows": public_rows,
        "row_count": len(public_rows),
        "sample_count": len(sorted_samples),
    }
    if len(sorted_samples) >= 2:
        result["delta_window"] = {
            "start_time": str(sorted_samples[0].get("timestamp") or ""),
            "finish_time": str(sorted_samples[-1].get("timestamp") or ""),
            "duration_seconds": max(
                float(sorted_samples[-1].get("monotonic") or 0.0)
                - float(sorted_samples[0].get("monotonic") or 0.0),
                0.0,
            ),
        }
    return result


def build_chart_result(metric: dict[str, Any], samples: list[dict[str, Any]]) -> dict[str, Any]:
    partition_by = [str(value) for value in metric.get("partition_by") or []]
    series_specs = list(metric.get("series") or [])
    grouped: dict[tuple[str, tuple[str, ...]], dict[str, Any]] = {}
    previous: dict[tuple[int, tuple[str, ...]], tuple[float, float]] = {}
    previous_ratios: dict[
        tuple[int, tuple[str, ...]],
        tuple[float, float, float],
    ] = {}
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
                if transform == "ratio_of_deltas":
                    denominator = _number(
                        _nested(row, str(spec.get("denominator_ref") or ""))
                    )
                    if denominator is None:
                        continue
                    old_ratio = previous_ratios.get(previous_key)
                    previous_ratios[previous_key] = (numeric, denominator, monotonic)
                    if (
                        old_ratio is None
                        or numeric < old_ratio[0]
                        or denominator < old_ratio[1]
                    ):
                        value = None
                    else:
                        denominator_delta = denominator - old_ratio[1]
                        value = (
                            (numeric - old_ratio[0])
                            / denominator_delta
                            * float(spec.get("scale") or 1.0)
                            if denominator_delta > 0
                            else None
                        )
                elif transform in {"rate", "delta"}:
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
