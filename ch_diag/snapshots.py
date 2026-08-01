"""Repeated ClickHouse and Linux sampling for snapshots reports."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from datetime import datetime, timedelta, timezone
import time
from typing import Any

from .artifact import item_from_plan
from .content_loader import ContentPack
from .database_adapter import DatabaseAdapter, DatabaseTarget
from .host import HostRunner
from .host_scripts import load_host_script, render_host_script
from .linux_helpers import _is_interesting_disk, normalize_iostat_row, parse_iostat_reports
from .planner import PlannedItem
from .samplers import (
    build_table_result,
    build_chart_result,
    apply_chart_budget,
    chart_coverage_diagnostics,
    clickhouse_thread_pool_rows,
    normalized_clickhouse_process_rows,
    normalized_clickhouse_thread_rows,
    normalized_linux_rows,
    parse_clickhouse_process,
    parse_linux_proc,
    utc_timestamp,
)
from .versioning import ClickHouseVersion, select_variant
from .runtime_config import (
    DEFAULT_DATABASE_WORKERS,
    DEFAULT_MAX_POINTS_PER_SERIES,
    DEFAULT_MAX_SERIES_PER_CHART,
    DEFAULT_MAX_TOTAL_CHART_POINTS,
    DEFAULT_SHELL_TIMEOUT_SECONDS,
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


def iostat_sampling_parameters(duration: float, interval: float) -> tuple[int, int]:
    interval_seconds = max(1, int(round(min(interval, duration))))
    points = max(1, int(duration // interval_seconds))
    return interval_seconds, points


def iostat_samples(
    output: str,
    *,
    started_at: datetime,
    started_monotonic: float,
    duration_seconds: float,
    interval_seconds: int,
    points: int,
) -> list[dict[str, Any]]:
    reports = parse_iostat_reports(output)
    if not reports:
        raise ValueError("iostat output contained no parseable device reports")
    interval_reports = reports[-points:] if len(reports) >= points else reports
    first_index = max(1, points - len(interval_reports) + 1)
    samples: list[dict[str, Any]] = []
    for report_offset, report in enumerate(interval_reports):
        index = first_index + report_offset
        elapsed = min(index * interval_seconds, duration_seconds)
        rows = [
            normalize_iostat_row(row)
            for row in report
            if _is_interesting_disk(str(row.get("device") or ""))
        ]
        timestamp = (started_at + timedelta(seconds=elapsed)).isoformat().replace(
            "+00:00", "Z"
        )
        samples.append(
            {
                "timestamp": timestamp,
                "monotonic": started_monotonic + elapsed,
                "rows": rows,
            }
        )
    return samples


async def _sleep_until(deadline: float) -> None:
    delay = deadline - time.monotonic()
    if delay > 0:
        await asyncio.sleep(delay)


def _sample_metadata(
    *,
    started_monotonic: float,
    scheduled_offset: float,
    sample_index: int,
) -> dict[str, Any]:
    sampled_monotonic = time.monotonic()
    return {
        "timestamp": utc_timestamp(),
        "monotonic": sampled_monotonic,
        "sample_index": sample_index,
        "scheduled_offset_seconds": scheduled_offset,
        "monotonic_offset_seconds": sampled_monotonic - started_monotonic,
    }


def _record_source_error(
    source_errors: dict[str, list[dict[str, Any]]],
    source_ids: set[str],
    *,
    level: str,
    code: str,
    message: str,
    coverage_incomplete: bool = False,
    failure_kind: str | None = None,
    failure_kind_evidence: str | None = None,
) -> None:
    for source_id in source_ids:
        diagnostic = {"level": level, "code": code, "message": message[:1000]}
        if coverage_incomplete:
            diagnostic["coverage_incomplete"] = True
        if failure_kind:
            diagnostic["failure_kind"] = failure_kind
        if failure_kind_evidence:
            diagnostic["failure_kind_evidence"] = failure_kind_evidence
        source_errors[source_id].append(diagnostic)


async def _run_scheduled_source(
    *,
    label: str,
    source_ids: set[str],
    schedule: list[tuple[int, float]],
    started_monotonic: float,
    source_errors: dict[str, list[dict[str, Any]]],
    collect_once: Callable[[int, float], Awaitable[None]],
) -> None:
    """Launch one source at absolute deadlines without overlapping itself."""

    active: asyncio.Task[None] | None = None

    async def guarded_collect(sample_index: int, offset: float) -> None:
        try:
            await collect_once(sample_index, offset)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            _record_source_error(
                source_errors,
                source_ids,
                level="error",
                code=type(exc).__name__,
                message=str(exc),
            )

    try:
        for sample_index, offset in schedule:
            await _sleep_until(started_monotonic + offset)
            if active is not None:
                if active.done():
                    await active
                    active = None
                else:
                    _record_source_error(
                        source_errors,
                        source_ids,
                        level="warning",
                        code="sample_skipped_source_busy",
                        message=(
                            f"scheduled {label} sample {sample_index} at +{offset:g}s "
                            "was skipped because the previous sample was still running"
                        ),
                    )
                    continue
            active = asyncio.create_task(guarded_collect(sample_index, offset))
        if active is not None:
            await active
    except asyncio.CancelledError:
        if active is not None and not active.done():
            active.cancel()
            await asyncio.gather(active, return_exceptions=True)
        raise


async def _collect_snapshot_markers(
    offsets: list[float],
    *,
    started_monotonic: float,
    snapshots: list[dict[str, Any]],
) -> None:
    for sample_index, offset in enumerate(offsets):
        await _sleep_until(started_monotonic + offset)
        metadata = _sample_metadata(
            started_monotonic=started_monotonic,
            scheduled_offset=offset,
            sample_index=sample_index,
        )
        snapshots.append(
            {
                "index": sample_index,
                "snapshot_time": metadata["timestamp"],
                "scheduled_offset_seconds": offset,
                "monotonic_offset_seconds": metadata["monotonic_offset_seconds"],
            }
        )


async def collect_metric_items(
    content: ContentPack,
    adapter: DatabaseAdapter | None,
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
    version: ClickHouseVersion | None = None
    if required_queries:
        if adapter is None:
            raise RuntimeError("database adapter is unavailable for SQL metric sources")
        raw_version = runtime_context.get("server_version")
        if not raw_version:
            raw_version = (await adapter.detect_runtime_context())["server_version"]
        version = ClickHouseVersion.parse(str(raw_version))
    query_sources: dict[str, tuple[str, float]] = {}
    unsupported_sources: dict[str, str] = {}
    for query_id in sorted(required_queries):
        assert version is not None
        manifest = content.queries[query_id]
        supported, unsupported_reason = await adapter.supports_requirements(
            manifest.get("requires")
        )
        if not supported:
            unsupported_sources[query_id] = str(unsupported_reason)
            continue
        variant = select_variant(
            list(manifest.get("variants") or []),
            version,
            target.scope,
            content.supported_lts_versions,
        )
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
    source_errors: dict[str, list[dict[str, Any]]] = {
        source_id: [] for source_id in required_samplers | required_queries
    }
    snapshots: list[dict[str, Any]] = []
    diagnostics: list[dict[str, Any]] = []
    proc_script: str | None = None
    iostat_script: str | None = None
    process_script: str | None = None
    max_process_threads = 0
    linux_samplers = {source_id for source_id in required_samplers if source_id.startswith("os.")}
    disk_samplers = linux_samplers & {"os.disk"}
    proc_samplers = linux_samplers - disk_samplers
    process_samplers = required_samplers & {
        "clickhouse.process",
        "clickhouse.threads",
        "clickhouse.thread_pools",
    }
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
            ) if proc_samplers else None
            iostat_script = render_host_script(
                (
                    content.path
                    / "scripts"
                    / str(provider_config.get("iostat_script") or "samplers/linux_iostat.sh")
                ).read_text(encoding="utf-8"),
                runtime_context,
            ) if disk_samplers else None
            if process_samplers:
                max_process_threads = int(provider_config.get("max_process_threads") or 2000)
                if max_process_threads < 1:
                    raise ValueError("ClickHouse process thread limit must be positive")
                process_manifest = {
                    "file": provider_config.get("process_script") or "samplers/clickhouse_process.sh",
                    "library": provider_config.get("process_library") or "lib/clickhouse_process.sh",
                }
                process_script = render_host_script(
                    load_host_script(content.path, process_manifest),
                    runtime_context,
                )

    offsets = schedule_offsets(duration_seconds, interval_seconds)
    schedule = list(enumerate(offsets))
    runtime_policy = content.report.get("runtime_policy") or {}
    shell_timeout = max(
        0.001,
        float(
            runtime_policy.get(
                "default_shell_timeout_seconds",
                DEFAULT_SHELL_TIMEOUT_SECONDS,
            )
        ),
    )
    sql_concurrency = max(
        1,
        int(runtime_policy.get("database_workers", DEFAULT_DATABASE_WORKERS)),
    )
    sql_semaphore = asyncio.Semaphore(sql_concurrency)
    started = time.monotonic()
    iostat_task: asyncio.Task[Any] | None = None
    iostat_started_at: datetime | None = None
    iostat_interval = 0
    iostat_points = 0
    if iostat_script is not None and host_runner is not None:
        iostat_interval, iostat_points = iostat_sampling_parameters(
            duration_seconds,
            interval_seconds,
        )
        iostat_started_at = datetime.now(timezone.utc)
        iostat_source = f"set -- {iostat_interval} {iostat_points + 1}\n{iostat_script}"
        iostat_task = asyncio.create_task(
            host_runner.run_script(iostat_source, timeout=duration_seconds + 2.0)
        )
    scheduled_tasks: list[asyncio.Task[None]] = [
        asyncio.create_task(
            _collect_snapshot_markers(
                offsets,
                started_monotonic=started,
                snapshots=snapshots,
            )
        )
    ]

    if proc_script is not None and host_runner is not None:
        previous_host: dict[str, Any] | None = None
        previous_host_mono: float | None = None

        async def collect_proc_once(sample_index: int, offset: float) -> None:
            nonlocal previous_host, previous_host_mono
            command = await host_runner.run_script(proc_script, timeout=shell_timeout)
            if command.returncode != 0:
                raise RuntimeError(command.stderr.strip() or f"exit code {command.returncode}")
            current_host = parse_linux_proc(command.stdout)
            metadata = _sample_metadata(
                started_monotonic=started,
                scheduled_offset=offset,
                sample_index=sample_index,
            )
            sampled_mono = float(metadata["monotonic"])
            rows_by_source = normalized_linux_rows(
                previous_host,
                current_host,
                None if previous_host_mono is None else sampled_mono - previous_host_mono,
            )
            for source_id in proc_samplers:
                sampler_samples[source_id].append(
                    {**metadata, "rows": rows_by_source.get(source_id, [])}
                )
            previous_host = current_host
            previous_host_mono = sampled_mono

        scheduled_tasks.append(
            asyncio.create_task(
                _run_scheduled_source(
                    label="procfs",
                    source_ids=proc_samplers,
                    schedule=schedule,
                    started_monotonic=started,
                    source_errors=source_errors,
                    collect_once=collect_proc_once,
                )
            )
        )

    if process_script is not None and host_runner is not None:
        previous_process: dict[str, Any] | None = None
        previous_process_mono: float | None = None
        selected_thread_ids: tuple[int, ...] | None = None
        selected_process_pid: int | None = None
        discovered_thread_count = 0
        thread_limit_reported = False
        thread_capture_reported = False
        thread_io_reported = False
        thread_sampler_ids = process_samplers & {
            "clickhouse.threads",
            "clickhouse.thread_pools",
        }

        async def collect_process_once(sample_index: int, offset: float) -> None:
            nonlocal previous_process, previous_process_mono
            nonlocal selected_thread_ids, selected_process_pid, discovered_thread_count
            nonlocal thread_limit_reported, thread_capture_reported, thread_io_reported
            if not thread_sampler_ids:
                arguments = "set -- process 1"
            elif selected_thread_ids is None:
                arguments = f"set -- discover {max_process_threads}"
            else:
                selected = ",".join(str(value) for value in selected_thread_ids)
                arguments = (
                    f"set -- selected {max_process_threads} {selected} "
                    f"{discovered_thread_count}"
                )
            command = await host_runner.run_script(
                arguments + "\n" + process_script,
                timeout=shell_timeout,
            )
            if command.returncode != 0:
                raise RuntimeError(command.stderr.strip() or f"exit code {command.returncode}")
            current_process = parse_clickhouse_process(command.stdout)
            coverage = current_process["thread_coverage"]
            if thread_sampler_ids and selected_thread_ids is None:
                selected_thread_ids = tuple(current_process["threads"]) or None
                selected_process_pid = int(current_process["pid"])
                discovered_thread_count = int(coverage["discovered_thread_count"])
            elif selected_process_pid != int(current_process["pid"]):
                selected_thread_ids = None
                selected_process_pid = None
                discovered_thread_count = 0
            if coverage["selection_truncated"] and not thread_limit_reported:
                _record_source_error(
                    source_errors,
                    thread_sampler_ids,
                    level="warning",
                    code="process_thread_limit",
                    message=(
                        "ClickHouse thread sampling was limited to "
                        f"{coverage['selected_thread_count']} of "
                        f"{coverage['discovered_thread_count']} discovered threads"
                    ),
                    coverage_incomplete=True,
                )
                thread_limit_reported = True
            if coverage["capture_incomplete"] and not thread_capture_reported:
                _record_source_error(
                    source_errors,
                    thread_sampler_ids,
                    level="warning",
                    code="process_thread_capture_incomplete",
                    message=(
                        "ClickHouse thread sampling captured "
                        f"{coverage['captured_thread_count']} of "
                        f"{coverage['selected_thread_count']} selected threads; "
                        "threads may have exited or procfs access may be incomplete"
                    ),
                    coverage_incomplete=True,
                )
                thread_capture_reported = True
            if coverage["io_capture_incomplete"] and not thread_io_reported:
                _record_source_error(
                    source_errors,
                    thread_sampler_ids,
                    level="warning",
                    code="process_thread_io_incomplete",
                    message=(
                        "ClickHouse thread I/O was readable for "
                        f"{coverage['io_captured_thread_count']} of "
                        f"{coverage['captured_thread_count']} captured threads"
                    ),
                )
                thread_io_reported = True
            metadata = _sample_metadata(
                started_monotonic=started,
                scheduled_offset=offset,
                sample_index=sample_index,
            )
            sampled_mono = float(metadata["monotonic"])
            elapsed_process = (
                None
                if previous_process_mono is None
                else sampled_mono - previous_process_mono
            )
            process_rows = normalized_clickhouse_process_rows(
                previous_process,
                current_process,
                elapsed_process,
            )
            thread_rows = normalized_clickhouse_thread_rows(
                previous_process,
                current_process,
                elapsed_process,
            )
            rows_by_source = {
                "clickhouse.process": process_rows,
                "clickhouse.threads": thread_rows,
                "clickhouse.thread_pools": clickhouse_thread_pool_rows(thread_rows),
            }
            for source_id in process_samplers:
                sample = {**metadata, "rows": rows_by_source[source_id]}
                if source_id in thread_sampler_ids:
                    sample["coverage"] = dict(coverage)
                sampler_samples[source_id].append(sample)
            previous_process = current_process
            previous_process_mono = sampled_mono

        scheduled_tasks.append(
            asyncio.create_task(
                _run_scheduled_source(
                    label="ClickHouse process/thread",
                    source_ids=process_samplers,
                    schedule=schedule,
                    started_monotonic=started,
                    source_errors=source_errors,
                    collect_once=collect_process_once,
                )
            )
        )

    for source_id in sorted(required_queries):
        source = query_sources.get(source_id)
        if source is None:
            _record_source_error(
                source_errors,
                {source_id},
                level="warning",
                code="unsupported",
                message=unsupported_sources.get(
                    source_id,
                    f"no {target.scope} source variant for ClickHouse {version}",
                ),
            )
            continue
        collection_scope = str(content.queries[source_id].get("collection_scope"))
        if collection_scope == "window_end":
            source_schedule = [schedule[-1]]
        elif collection_scope == "once":
            source_schedule = [schedule[0]]
        else:
            source_schedule = schedule

        async def collect_query_once(
            sample_index: int,
            offset: float,
            *,
            query_id: str = source_id,
            query_source: tuple[str, float] = source,
        ) -> None:
            assert adapter is not None
            async with sql_semaphore:
                execution = await adapter.execute_query(
                    query_source[0],
                    target=target,
                    timeout_seconds=query_source[1],
                    optional_capability=bool(content.queries[query_id].get("optional")),
                )
            metadata = _sample_metadata(
                started_monotonic=started,
                scheduled_offset=offset,
                sample_index=sample_index,
            )
            status = str(execution["collection_status"])
            if status not in {"ok", "empty"}:
                execution_diagnostics = [
                    diagnostic
                    for diagnostic in execution.get("diagnostics") or []
                    if isinstance(diagnostic, dict)
                ]
                if execution_diagnostics:
                    for diagnostic in execution_diagnostics:
                        _record_source_error(
                            source_errors,
                            {query_id},
                            level=str(
                                diagnostic.get("level")
                                or ("error" if status in {"error", "timeout"} else "warning")
                            ),
                            code=str(diagnostic.get("code") or status),
                            message=str(
                                diagnostic.get("message")
                                or execution.get("reason")
                                or status
                            ),
                            coverage_incomplete=(
                                diagnostic.get("coverage_incomplete") is True
                            ),
                            failure_kind=(
                                str(diagnostic["failure_kind"])
                                if diagnostic.get("failure_kind")
                                else None
                            ),
                            failure_kind_evidence=(
                                str(diagnostic["failure_kind_evidence"])
                                if diagnostic.get("failure_kind_evidence")
                                else None
                            ),
                        )
                else:
                    _record_source_error(
                        source_errors,
                        {query_id},
                        level="error" if status in {"error", "timeout"} else "warning",
                        code=status,
                        message=str(execution.get("reason") or status),
                    )
                return
            result = execution["result"]
            columns = [str(column["name"]) for column in result.get("columns") or []]
            rows = [dict(zip(columns, row)) for row in result.get("rows") or []]
            query_samples[query_id].append({**metadata, "rows": rows})

        scheduled_tasks.append(
            asyncio.create_task(
                _run_scheduled_source(
                    label=f"SQL source {source_id}",
                    source_ids={source_id},
                    schedule=source_schedule,
                    started_monotonic=started,
                    source_errors=source_errors,
                    collect_once=collect_query_once,
                )
            )
        )

    try:
        await asyncio.gather(*scheduled_tasks)
    except BaseException:
        for task in scheduled_tasks:
            if not task.done():
                task.cancel()
        await asyncio.gather(*scheduled_tasks, return_exceptions=True)
        if iostat_task is not None and not iostat_task.done():
            iostat_task.cancel()
            await asyncio.gather(iostat_task, return_exceptions=True)
        raise

    if iostat_task is not None and iostat_started_at is not None:
        try:
            command = await iostat_task
            if command.returncode != 0:
                raise RuntimeError(command.stderr.strip() or f"exit code {command.returncode}")
            sampler_samples["os.disk"].extend(
                iostat_samples(
                    command.stdout,
                    started_at=iostat_started_at,
                    started_monotonic=started,
                    duration_seconds=duration_seconds,
                    interval_seconds=iostat_interval,
                    points=iostat_points,
                )
            )
        except Exception as exc:
            _record_source_error(
                source_errors,
                disk_samplers,
                level="error",
                code=type(exc).__name__,
                message=str(exc),
            )

    items: dict[str, dict[str, Any]] = {}
    for planned in planned_items:
        metric = metrics[planned.source_id]
        source_id = str(metric.get("source_sampler") or metric.get("source_query") or "")
        samples = sampler_samples.get(source_id) or query_samples.get(source_id) or []
        result_kind = str((metric.get("result_contract") or {}).get("kind") or "chart")
        result = (
            build_table_result(metric, samples)
            if result_kind == "table"
            else build_chart_result(metric, samples)
        )
        if source_id in {"clickhouse.threads", "clickhouse.thread_pools"}:
            coverage_samples = [
                {
                    "sample_index": sample.get("sample_index"),
                    **sample["coverage"],
                }
                for sample in samples
                if isinstance(sample.get("coverage"), dict)
            ]
            if coverage_samples:
                result["coverage"] = {"samples": coverage_samples}
                result["coverage_incomplete"] = any(
                    coverage.get("selection_truncated")
                    or coverage.get("capture_incomplete")
                    for coverage in coverage_samples
                )
        errors = source_errors.get(source_id) or []
        coverage_diagnostics = chart_coverage_diagnostics(result) if result_kind == "chart" else []
        budget_diagnostics = (
            apply_chart_budget(
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
            if result_kind == "chart"
            else []
        )
        required_fields = [str(value) for value in metric.get("requires_fields") or []]
        required_fields_observed = not required_fields or any(
            any(row.get(field) is not None for field in required_fields)
            for sample in samples
            for row in sample.get("rows") or []
        )
        if required_fields and not required_fields_observed and samples:
            status = "unsupported"
            reason = (
                "host permissions or kernel policy do not expose required process fields: "
                + ", ".join(required_fields)
            )
        elif (
            result.get("series_count", 0) if result_kind == "chart" else result.get("row_count", 0)
        ):
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
            source_language="sql" if metric.get("source_query") else "bash",
        )
        items[planned.item_id] = item
        diagnostics.extend(
            {"source_id": source_id, "item_id": planned.item_id, **entry}
            for entry in [*coverage_diagnostics, *budget_diagnostics]
        )
    for source_id, errors in source_errors.items():
        diagnostics.extend({"source_id": source_id, **error} for error in errors)
    return items, snapshots, diagnostics
