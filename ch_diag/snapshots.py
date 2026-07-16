"""Repeated ClickHouse and Linux sampling for snapshots reports."""

from __future__ import annotations

import asyncio
import time
from typing import Any

from .artifact import item_from_plan
from .content_loader import ContentPack
from .database_adapter import DatabaseAdapter, DatabaseTarget
from .host import HostRunner
from .host_scripts import load_host_script, render_host_script
from .planner import PlannedItem
from .samplers import (
    build_chart_result,
    apply_chart_budget,
    chart_coverage_diagnostics,
    normalized_clickhouse_process_rows,
    normalized_linux_rows,
    parse_clickhouse_process,
    parse_linux_proc,
    utc_timestamp,
)
from .versioning import ClickHouseVersion, select_variant
from .runtime_config import (
    DEFAULT_MAX_POINTS_PER_SERIES,
    DEFAULT_MAX_SERIES_PER_CHART,
    DEFAULT_MAX_TOTAL_CHART_POINTS,
)


def schedule_offsets(duration: float, interval: float) -> list[float]:
    if duration <= 0:
        raise ValueError("snapshot duration must be greater than zero")
    if interval <= 0:
        raise ValueError("snapshot interval must be greater than zero")
    offsets = [0.0]
    next_offset = interval
    while next_offset < duration:
        offsets.append(next_offset)
        next_offset += interval
    offsets.append(duration)
    return offsets


async def collect_metric_items(
    content: ContentPack,
    adapter: DatabaseAdapter,
    target: DatabaseTarget,
    planned_items: list[PlannedItem],
    host_runner: HostRunner | None,
    runtime_context: dict[str, Any],
    *,
    duration_seconds: float,
    interval_seconds: float,
) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    metrics = {item.source_id: content.metrics[item.source_id] for item in planned_items}
    required_samplers = {
        str(metric["source_sampler"])
        for metric in metrics.values()
        if metric.get("source_sampler")
    }
    required_queries = {
        str(metric["source_query"])
        for metric in metrics.values()
        if metric.get("source_query")
    }
    version = ClickHouseVersion.parse((await adapter.detect_runtime_context())["server_version"])
    query_sources: dict[str, tuple[str, float]] = {}
    unsupported_sources: dict[str, str] = {}
    for query_id in sorted(required_queries):
        manifest = content.queries[query_id]
        supported, unsupported_reason = await adapter.supports_requirements(
            manifest.get("requires")
        )
        if not supported:
            unsupported_sources[query_id] = str(unsupported_reason)
            continue
        variant = select_variant(list(manifest.get("variants") or []), version, target.scope)
        if variant is None:
            continue
        path = content.path / "queries" / str(variant["sql_file"])
        query_sources[query_id] = (
            path.read_text(encoding="utf-8"),
            float(manifest.get("timeout_seconds", 5.0)),
        )

    sampler_samples: dict[str, list[dict[str, Any]]] = {
        source_id: [] for source_id in required_samplers
    }
    query_samples: dict[str, list[dict[str, Any]]] = {
        source_id: [] for source_id in required_queries
    }
    source_errors: dict[str, list[dict[str, str]]] = {
        source_id: [] for source_id in required_samplers | required_queries
    }
    snapshots: list[dict[str, Any]] = []
    diagnostics: list[dict[str, Any]] = []
    proc_script: str | None = None
    process_script: str | None = None
    linux_samplers = {source_id for source_id in required_samplers if source_id.startswith("os.")}
    process_samplers = required_samplers & {"clickhouse.process"}
    if required_samplers:
        if host_runner is None:
            for source_id in required_samplers:
                source_errors[source_id].append(
                    {"level": "error", "code": "host_unavailable", "message": "host sampling is unavailable"}
                )
        else:
            provider = content.sampler_providers.get("linux_os") or {}
            provider_config = provider.get("config") or {}
            proc_script = render_host_script(
                (content.path / "scripts" / str(provider_config.get("proc_script") or "samplers/linux_proc.sh")).read_text(encoding="utf-8"),
                runtime_context,
            ) if linux_samplers else None
            if process_samplers:
                process_manifest = {
                    "file": provider_config.get("process_script") or "samplers/clickhouse_process.sh",
                    "library": provider_config.get("process_library") or "lib/clickhouse_process.sh",
                }
                process_script = render_host_script(
                    load_host_script(content.path, process_manifest),
                    runtime_context,
                )

    offsets = schedule_offsets(duration_seconds, interval_seconds)
    started = time.monotonic()
    previous_host: dict[str, Any] | None = None
    previous_host_mono: float | None = None
    previous_process: dict[str, Any] | None = None
    previous_process_mono: float | None = None
    for index, offset in enumerate(offsets):
        delay = started + offset - time.monotonic()
        if delay > 0:
            await asyncio.sleep(delay)
        timestamp = utc_timestamp()
        now_mono = time.monotonic()
        snapshots.append(
            {"index": index, "snapshot_time": timestamp, "monotonic_offset_seconds": now_mono - started}
        )

        if proc_script is not None and host_runner is not None:
            try:
                command = await host_runner.run_script(proc_script, timeout=2.0)
                if command.returncode != 0:
                    raise RuntimeError(command.stderr.strip() or f"exit code {command.returncode}")
                current_host = parse_linux_proc(command.stdout)
                rows_by_source = normalized_linux_rows(
                    previous_host,
                    current_host,
                    None if previous_host_mono is None else now_mono - previous_host_mono,
                )
                for source_id in required_samplers:
                    sampler_samples[source_id].append(
                        {
                            "timestamp": timestamp,
                            "monotonic": now_mono,
                            "rows": rows_by_source.get(source_id, []),
                        }
                    )
                previous_host = current_host
                previous_host_mono = now_mono
            except Exception as exc:
                for source_id in linux_samplers:
                    source_errors[source_id].append(
                        {"level": "error", "code": type(exc).__name__, "message": str(exc)[:1000]}
                    )

        if process_script is not None and host_runner is not None:
            try:
                command = await host_runner.run_script(process_script, timeout=2.0)
                if command.returncode != 0:
                    raise RuntimeError(command.stderr.strip() or f"exit code {command.returncode}")
                current_process = parse_clickhouse_process(command.stdout)
                process_rows = normalized_clickhouse_process_rows(
                    previous_process,
                    current_process,
                    None if previous_process_mono is None else now_mono - previous_process_mono,
                )
                for source_id in process_samplers:
                    sampler_samples[source_id].append(
                        {"timestamp": timestamp, "monotonic": now_mono, "rows": process_rows}
                    )
                previous_process = current_process
                previous_process_mono = now_mono
            except Exception as exc:
                for source_id in process_samplers:
                    source_errors[source_id].append(
                        {"level": "error", "code": type(exc).__name__, "message": str(exc)[:1000]}
                    )

        for source_id in sorted(required_queries):
            source = query_sources.get(source_id)
            if source is None:
                source_errors[source_id].append(
                    {
                        "level": "warning",
                        "code": "unsupported",
                        "message": unsupported_sources.get(
                            source_id,
                            f"no {target.scope} source variant for ClickHouse {version}",
                        ),
                    }
                )
                continue
            execution = await adapter.execute_query(
                source[0],
                target=target,
                timeout_seconds=source[1],
                optional_capability=bool(content.queries[source_id].get("optional")),
            )
            status = str(execution["collection_status"])
            if status not in {"ok", "empty"}:
                source_errors[source_id].append(
                    {
                        "level": "error" if status == "error" else "warning",
                        "code": status,
                        "message": str(execution.get("reason") or status)[:1000],
                    }
                )
                continue
            result = execution["result"]
            columns = [str(column["name"]) for column in result.get("columns") or []]
            rows = [dict(zip(columns, row)) for row in result.get("rows") or []]
            query_samples[source_id].append(
                {"timestamp": timestamp, "monotonic": now_mono, "rows": rows}
            )

    items: dict[str, dict[str, Any]] = {}
    runtime_policy = content.report.get("runtime_policy") or {}
    for planned in planned_items:
        metric = metrics[planned.source_id]
        source_id = str(metric.get("source_sampler") or metric.get("source_query") or "")
        samples = sampler_samples.get(source_id) or query_samples.get(source_id) or []
        result = build_chart_result(metric, samples)
        errors = source_errors.get(source_id) or []
        coverage_diagnostics = chart_coverage_diagnostics(result)
        budget_diagnostics = apply_chart_budget(
            result,
            max_series=int(
                runtime_policy.get("max_series_per_chart", DEFAULT_MAX_SERIES_PER_CHART)
            ),
            max_points_per_series=int(
                runtime_policy.get(
                    "max_points_per_series",
                    DEFAULT_MAX_POINTS_PER_SERIES,
                )
            ),
            max_total_points=int(
                runtime_policy.get(
                    "max_total_chart_points",
                    DEFAULT_MAX_TOTAL_CHART_POINTS,
                )
            ),
        )
        required_fields = [str(value) for value in metric.get("requires_fields") or []]
        required_fields_observed = not required_fields or any(
            any(row.get(field) is not None for field in required_fields)
            for sample in samples
            for row in sample.get("rows") or []
        )
        if required_fields and not required_fields_observed:
            status = "unsupported"
            reason = (
                "host permissions or kernel policy do not expose required process fields: "
                + ", ".join(required_fields)
            )
        elif result["series_count"]:
            status, reason = "ok", None
        elif errors and all(error.get("code") == "unsupported" for error in errors):
            status, reason = "unsupported", errors[0]["message"]
        elif errors:
            status, reason = "error", errors[0]["message"]
        else:
            status, reason = "empty", None
        source_text = query_sources.get(source_id, (None, 0.0))[0]
        item = item_from_plan(
            planned,
            collection_status=status,
            reason=reason,
            result=result,
            diagnostics=[*errors, *coverage_diagnostics, *budget_diagnostics],
            source_text=source_text,
            source_language="sql" if source_text else "bash",
        )
        items[planned.item_id] = item
        diagnostics.extend(
            {"source_id": source_id, "item_id": planned.item_id, **entry}
            for entry in [*coverage_diagnostics, *budget_diagnostics]
        )
    for source_id, errors in source_errors.items():
        diagnostics.extend({"source_id": source_id, **error} for error in errors)
    return items, snapshots, diagnostics
