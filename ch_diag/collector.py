"""One-shot collection lifecycle for schema-version-5 ch_diag reports."""

from __future__ import annotations

import json
from pathlib import Path
import re
import sys
import time
from typing import Any, Iterable

from .artifact import (
    FAILED_COLLECTION_STATUSES,
    create_artifact,
    finalize_collection_summary,
    item_from_plan,
    omit_uncollected_items,
    strip_artifact_metadata,
    utc_now,
    validate_artifact,
    write_json,
    write_text_secure,
)
from .artifact_schema import column_descriptor
from .content_loader import ContentPack
from .database_adapter import (
    DatabaseAdapter,
    DatabaseAdapterFactory,
    DatabaseConnectionConfig,
    DatabaseTarget,
)
from .errors import ChDiagError
from .host import HostRunner, LocalHostRunner
from .host_scripts import load_host_script, render_host_script
from .planner import PlannedItem, build_plan, collection_requirements
from .progress import ProgressReporter
from .render.html import render_html
from .runtime_config import (
    CLUSTER_SCOPE,
    DEFAULT_MAX_CLUSTER_TARGETS,
    DEFAULT_MAX_ARTIFACT_BYTES,
    DEFAULT_SNAPSHOT_DURATION_SECONDS,
    DEFAULT_SNAPSHOT_INTERVAL_SECONDS,
    LOCAL_COLLECTION_MODE,
    MIN_SNAPSHOT_INTERVAL_SECONDS,
    MAX_SNAPSHOT_COUNT,
    ONE_SHOT_MODE,
    REMOTE_COLLECTION_MODE,
    SNAPSHOTS_MODE,
)
from .snapshots import collect_metric_items, schedule_offsets
from .ssh_transport import SshConfig, SshSession
from .versioning import ClickHouseVersion


async def collect_one_shot(
    content: ContentPack,
    connection: DatabaseConnectionConfig,
    *,
    out_dir: str | Path,
    collection_mode: str,
    target_scope: str,
    cluster_name: str | None = None,
    item_ids: str | Iterable[str] | None = None,
    tags: str | Iterable[str] | None = None,
    output_formats: Iterable[str] = ("json", "html"),
    json_out: str | Path | None = None,
    html_out: str | Path | None = None,
    strip_meta: bool = False,
    ssh_config: SshConfig | None = None,
    progress: ProgressReporter | None = None,
    adapter_factory: DatabaseAdapterFactory | None = None,
) -> list[dict[str, Any]]:
    return await _collect(
        content,
        connection,
        out_dir=out_dir,
        run_mode=ONE_SHOT_MODE,
        collection_mode=collection_mode,
        target_scope=target_scope,
        cluster_name=cluster_name,
        item_ids=item_ids,
        tags=tags,
        output_formats=output_formats,
        json_out=json_out,
        html_out=html_out,
        strip_meta=strip_meta,
        ssh_config=ssh_config,
        progress=progress,
        adapter_factory=adapter_factory,
        duration_seconds=0.0,
        interval_seconds=0.0,
    )


async def collect_snapshots(
    content: ContentPack,
    connection: DatabaseConnectionConfig,
    *,
    out_dir: str | Path,
    collection_mode: str,
    target_scope: str,
    cluster_name: str | None = None,
    item_ids: str | Iterable[str] | None = None,
    tags: str | Iterable[str] | None = None,
    output_formats: Iterable[str] = ("json", "html"),
    json_out: str | Path | None = None,
    html_out: str | Path | None = None,
    strip_meta: bool = False,
    ssh_config: SshConfig | None = None,
    progress: ProgressReporter | None = None,
    duration_seconds: float = DEFAULT_SNAPSHOT_DURATION_SECONDS,
    interval_seconds: float = DEFAULT_SNAPSHOT_INTERVAL_SECONDS,
    adapter_factory: DatabaseAdapterFactory | None = None,
) -> list[dict[str, Any]]:
    if interval_seconds < MIN_SNAPSHOT_INTERVAL_SECONDS:
        raise ValueError(
            f"--interval must be at least {MIN_SNAPSHOT_INTERVAL_SECONDS:g} seconds"
        )
    if duration_seconds < interval_seconds:
        raise ValueError("--duration must be greater than or equal to --interval")
    snapshot_count = len(schedule_offsets(duration_seconds, interval_seconds))
    policy = content.report.get("runtime_policy") or {}
    max_snapshot_count = int(policy.get("max_snapshot_count", MAX_SNAPSHOT_COUNT))
    if snapshot_count > max_snapshot_count:
        raise ValueError(
            f"snapshot window produces {snapshot_count} samples, above limit "
            f"{max_snapshot_count}; increase --interval or reduce --duration"
        )
    return await _collect(
        content,
        connection,
        out_dir=out_dir,
        run_mode=SNAPSHOTS_MODE,
        collection_mode=collection_mode,
        target_scope=target_scope,
        cluster_name=cluster_name,
        item_ids=item_ids,
        tags=tags,
        output_formats=output_formats,
        json_out=json_out,
        html_out=html_out,
        strip_meta=strip_meta,
        ssh_config=ssh_config,
        progress=progress,
        adapter_factory=adapter_factory,
        duration_seconds=duration_seconds,
        interval_seconds=interval_seconds,
    )


async def _collect(
    content: ContentPack,
    connection: DatabaseConnectionConfig,
    *,
    out_dir: str | Path,
    run_mode: str,
    collection_mode: str,
    target_scope: str,
    cluster_name: str | None,
    item_ids: str | Iterable[str] | None,
    tags: str | Iterable[str] | None,
    output_formats: Iterable[str],
    json_out: str | Path | None,
    html_out: str | Path | None,
    strip_meta: bool,
    ssh_config: SshConfig | None,
    progress: ProgressReporter | None,
    duration_seconds: float,
    interval_seconds: float,
    adapter_factory: DatabaseAdapterFactory | None,
) -> list[dict[str, Any]]:
    ssh: SshSession | None = None
    adapter: DatabaseAdapter | None = None
    effective_connection = connection
    host_runner: HostRunner | None = None
    requirements = collection_requirements(
        content,
        mode=run_mode,
        collection_mode=collection_mode,
        target_scope=target_scope,
        item_ids=item_ids,
        tags=tags,
    )
    try:
        if collection_mode == REMOTE_COLLECTION_MODE:
            if requirements.requires_ssh(collection_mode) and ssh_config is None:
                raise ValueError("remote collection requires SSH options")
            if requirements.requires_ssh(collection_mode):
                assert ssh_config is not None
                ssh = await SshSession.connect(ssh_config)
                host_runner = ssh
            if requirements.requires_database:
                assert ssh is not None
                local_host, local_port = await ssh.open_tunnel(
                    connection.host,
                    connection.port,
                )
                effective_connection = connection.tunneled(local_host, local_port)
        elif ssh_config is not None:
            raise ValueError("SSH options are only valid in remote collection mode")
        elif collection_mode == LOCAL_COLLECTION_MODE and requirements.requires_host:
            host_runner = LocalHostRunner()

        policy = content.report.get("runtime_policy") or {}
        runtime_context: dict[str, Any] = {
            "targets": list(requirements.targets),
            "database_connected": requirements.requires_database,
            "database_host_ip": connection.host,
            "database_port": connection.port,
        }
        if requirements.requires_database:
            if adapter_factory is None:
                raise ValueError("database adapter factory is required")
            adapter = adapter_factory(effective_connection, policy)
            runtime_context.update(await adapter.detect_runtime_context())
            # The adapter may be connected to an ephemeral local SSH tunnel.
            runtime_context["database_host_ip"] = connection.host
            runtime_context["database_port"] = connection.port
        if host_runner is not None:
            runtime_context["host_collection_hostname"] = await host_runner.hostname()
        targets = (
            await adapter.resolve_targets(target_scope, cluster_name)
            if adapter is not None
            else [DatabaseTarget(scope="node")]
        )
        max_targets = int(
            policy.get("max_cluster_targets", DEFAULT_MAX_CLUSTER_TARGETS)
        )
        if len(targets) > max_targets:
            raise ValueError(
                f"database target selection resolved to {len(targets)} targets, "
                f"above limit {max_targets}"
            )
        runtime_context["resolved_target_count"] = len(targets)
        runtime_context["target_selector"] = cluster_name
        if len(targets) > 1 and (json_out is not None or html_out is not None):
            raise ValueError("explicit --json-out/--html-out cannot be combined with cluster-name=ALL")
        artifacts: list[dict[str, Any]] = []
        for target in targets:
            artifacts.append(
                await _collect_target(
                    content,
                    adapter,
                    runtime_context,
                    target,
                    out_dir=out_dir,
                    run_mode=run_mode,
                    collection_mode=collection_mode,
                    host_runner=host_runner,
                    item_ids=item_ids,
                    tags=tags,
                    output_formats=set(output_formats),
                    json_out=json_out,
                    html_out=html_out,
                    strip_meta=strip_meta,
                    progress=progress,
                    multiple_targets=len(targets) > 1,
                    duration_seconds=duration_seconds,
                    interval_seconds=interval_seconds,
                )
            )
        return artifacts
    finally:
        await _close_collection_resources(
            adapter,
            ssh,
            suppress_errors=sys.exc_info()[0] is not None,
        )


async def _close_collection_resources(
    adapter: DatabaseAdapter | None,
    ssh: SshSession | None,
    *,
    suppress_errors: bool,
) -> None:
    """Close both resources even when one cleanup path fails."""

    errors: list[BaseException] = []
    for resource in (adapter, ssh):
        if resource is None:
            continue
        try:
            await resource.close()
        except BaseException as exc:
            errors.append(exc)
    if errors and not suppress_errors:
        raise errors[0]


async def _collect_target(
    content: ContentPack,
    adapter: DatabaseAdapter | None,
    runtime_context: dict[str, Any],
    target: DatabaseTarget,
    *,
    out_dir: str | Path,
    run_mode: str,
    collection_mode: str,
    host_runner: HostRunner | None,
    item_ids: str | Iterable[str] | None,
    tags: str | Iterable[str] | None,
    output_formats: set[str],
    json_out: str | Path | None,
    html_out: str | Path | None,
    strip_meta: bool,
    progress: ProgressReporter | None,
    multiple_targets: bool,
    duration_seconds: float,
    interval_seconds: float,
) -> dict[str, Any]:
    version = (
        ClickHouseVersion.parse(str(runtime_context["server_version"]))
        if runtime_context.get("server_version")
        else None
    )
    plan = build_plan(
        content,
        version,
        mode=run_mode,
        collection_mode=collection_mode,
        target_scope=target.scope,
        item_ids=item_ids,
        tags=tags,
    )
    started_at = utc_now()
    artifact = create_artifact(content, plan, dict(runtime_context), target, started_at=started_at)
    if progress is not None:
        progress.configure(len(plan.items))
        progress.info(
            f"START mode={run_mode} target_scope={target.scope} "
            f"cluster={target.cluster_name or '-'} items={len(plan.items)}"
        )
    omitted: set[str] = set()
    metric_items: list[PlannedItem] = []
    fail_fast = bool((content.report.get("runtime_policy") or {}).get("fail_fast", False))
    for planned in plan.items:
        if planned.status != "planned":
            omitted.add(planned.item_id)
            if progress is not None:
                progress.item(planned.item_id, "skipped", planned.reason)
            continue
        if planned.source_kind == "metric":
            metric_items.append(planned)
            continue
        item = await _execute_item_safely(
            content,
            adapter,
            target,
            planned,
            host_runner,
            runtime_context,
        )
        if item.get("collection_status") == "unsupported":
            omitted.add(planned.item_id)
            if progress is not None:
                progress.item(planned.item_id, "unsupported", item.get("reason"))
            continue
        artifact["items"][planned.item_id] = item
        if progress is not None:
            progress.item(planned.item_id, str(item["collection_status"]), item.get("reason"))
        _raise_if_fail_fast(fail_fast, item)
    if metric_items:
        try:
            collected_metrics, snapshots, diagnostics = await collect_metric_items(
                content,
                adapter,
                target,
                metric_items,
                host_runner,
                runtime_context,
                duration_seconds=duration_seconds,
                interval_seconds=interval_seconds,
            )
        except Exception as exc:
            collected_metrics = {
                planned.item_id: _item_error_from_exception(planned, exc)
                for planned in metric_items
            }
            snapshots = []
            diagnostics = []
        artifact["snapshots"] = snapshots
        artifact["diagnostics"].extend(diagnostics)
        for planned in metric_items:
            item = collected_metrics[planned.item_id]
            if item.get("collection_status") == "unsupported":
                omitted.add(planned.item_id)
                if progress is not None:
                    progress.item(planned.item_id, "unsupported", item.get("reason"))
                continue
            artifact["items"][planned.item_id] = item
            if progress is not None:
                progress.item(
                    planned.item_id,
                    str(item["collection_status"]),
                    item.get("reason"),
                )
            _raise_if_fail_fast(fail_fast, item)
    omit_uncollected_items(artifact, omitted)
    artifact["runtime"]["finished_at"] = utc_now()
    finalize_collection_summary(artifact)
    if strip_meta:
        strip_artifact_metadata(artifact)
    validate_artifact(artifact)
    json_path, html_path = _output_paths(
        out_dir,
        target,
        output_formats,
        json_out=json_out,
        html_out=html_out,
        multiple_targets=multiple_targets,
    )
    max_bytes = int(
        (content.report.get("runtime_policy") or {}).get(
            "max_artifact_bytes",
            DEFAULT_MAX_ARTIFACT_BYTES,
        )
    )
    if json_path is not None:
        write_json(json_path, artifact, max_bytes=max_bytes)
    if html_path is not None:
        write_text_secure(html_path, render_html(artifact), max_bytes=max_bytes * 12)
    artifact["runtime"]["output_json"] = str(json_path) if json_path else None
    artifact["runtime"]["output_html"] = str(html_path) if html_path else None
    if progress is not None:
        progress.info(
            f"FINISH status={artifact['runtime']['completion_status']} "
            + " ".join(
                part
                for part in (
                    f"json={json_path}" if json_path else "",
                    f"html={html_path}" if html_path else "",
                )
                if part
            )
        )
    return artifact


async def _execute_item_safely(
    content: ContentPack,
    adapter: DatabaseAdapter | None,
    target: DatabaseTarget,
    planned: PlannedItem,
    host_runner: HostRunner | None,
    runtime_context: dict[str, Any],
) -> dict[str, Any]:
    try:
        primary = await _execute_item(
            content,
            adapter,
            target,
            planned,
            host_runner,
            runtime_context,
        )
    except Exception as exc:
        primary = _item_error_from_exception(planned, exc)
    trigger = _fallback_trigger(primary, planned.fallback_on)
    if trigger is None or planned.fallback_item is None:
        return primary
    try:
        fallback = await _execute_item(
            content,
            adapter,
            target,
            planned.fallback_item,
            host_runner,
            runtime_context,
        )
    except Exception as exc:
        fallback = _item_error_from_exception(planned.fallback_item, exc)
    return _replace_with_fallback_item(
        planned,
        primary,
        planned.fallback_item,
        fallback,
        trigger,
    )


def _item_error_from_exception(planned: PlannedItem, exc: BaseException) -> dict[str, Any]:
    message = _redact_exception(exc)
    return item_from_plan(
        planned,
        collection_status="error",
        reason=message,
        result={"kind": "none"},
        diagnostics=[
            {
                "level": "error",
                "code": type(exc).__name__,
                "message": message,
                "exception_type": type(exc).__name__,
            }
        ],
    )


def _fallback_trigger(item: dict[str, Any], allowed: tuple[str, ...]) -> str | None:
    if item.get("collection_status") in {"ok", "empty"} or not allowed:
        return None
    allowed_set = set(allowed)
    for diagnostic in item.get("diagnostics") or []:
        if not isinstance(diagnostic, dict):
            continue
        failure = diagnostic.get("failure_kind")
        if isinstance(failure, str) and failure in allowed_set:
            return failure
        code = diagnostic.get("code")
        if isinstance(code, str) and code in allowed_set:
            return code
    return None


def _replace_with_fallback_item(
    parent_plan: PlannedItem,
    primary_item: dict[str, Any],
    fallback_plan: PlannedItem,
    fallback_item: dict[str, Any],
    trigger: str,
) -> dict[str, Any]:
    primary_timing = _numeric_timing(primary_item.get("timing_ms"))
    fallback_timing = _numeric_timing(fallback_item.get("timing_ms"))
    metadata = dict(fallback_item.get("source_metadata") or {})
    primary_metadata = primary_item.get("source_metadata") or {}
    parent_tags = primary_metadata.get("tags")
    if isinstance(parent_tags, list):
        metadata["tags"] = list(parent_tags)
    metadata["fallback"] = {
        "used": True,
        "trigger": trigger,
        "on": list(parent_plan.fallback_on),
        "parent_item_id": parent_plan.item_id,
        "parent_title": parent_plan.title,
        "fallback_item_id": fallback_plan.item_id,
        "effective_item_id": fallback_plan.item_id,
        "primary_source_kind": parent_plan.source_kind,
        "primary_source_id": parent_plan.source_id,
        "primary_reason": primary_item.get("reason"),
        "primary_timing_ms": primary_timing,
        "fallback_timing_ms": fallback_timing,
        "primary_diagnostics": primary_item.get("diagnostics") or [],
        "primary_instructions": primary_metadata.get("instructions"),
        "primary_source_text": primary_metadata.get("source_text"),
    }
    diagnostics = list(fallback_item.get("diagnostics") or [])
    diagnostics.insert(
        0,
        {
            "level": "warning",
            "code": "fallback_item_activated",
            "message": (
                f"Primary item {parent_plan.item_id} failed with {trigger}; "
                f"executed fallback item {fallback_plan.item_id}."
            ),
            "trigger": trigger,
            "parent_item_id": parent_plan.item_id,
            "fallback_item_id": fallback_plan.item_id,
        },
    )
    fallback_status = str(fallback_item.get("collection_status") or "error")
    if fallback_status in {"ok", "empty"}:
        reason = (
            f"Primary item failed ({trigger}); fallback item "
            f"{fallback_plan.item_id} was collected."
        )
    else:
        reason = (
            f"Primary item failed ({trigger}); fallback item {fallback_plan.item_id} "
            f"failed: {fallback_item.get('reason') or fallback_status}"
        )
    return {
        **fallback_item,
        "item_id": parent_plan.item_id,
        "section_id": parent_plan.section_id,
        "item_key": parent_plan.item_key,
        "title": f"[Fallback] {fallback_item.get('title') or fallback_plan.title}",
        "state": parent_plan.state,
        "reason": reason,
        "timing_ms": round(primary_timing + fallback_timing, 3),
        "source_metadata": metadata,
        "diagnostics": diagnostics,
    }


def _numeric_timing(value: Any) -> float:
    return float(value) if isinstance(value, (int, float)) else 0.0


def _raise_if_fail_fast(enabled: bool, item: dict[str, Any]) -> None:
    if not enabled or item.get("collection_status") not in FAILED_COLLECTION_STATUSES:
        return
    raise ChDiagError(
        "fail_fast stopped collection at "
        f"{item.get('item_id') or '<unknown>'}: {item.get('reason') or 'collection failed'}"
    )


async def _execute_item(
    content: ContentPack,
    adapter: DatabaseAdapter | None,
    target: DatabaseTarget,
    planned: PlannedItem,
    host_runner: HostRunner | None,
    runtime_context: dict[str, Any],
) -> dict[str, Any]:
    if planned.source_kind == "query":
        if adapter is None:
            raise ChDiagError("database adapter is unavailable for a query item")
        sql_path = content.path / "queries" / str(planned.sql_file)
        sql = sql_path.read_text(encoding="utf-8")
        manifest = content.queries[planned.source_id]
        supported, unsupported_reason = await adapter.supports_requirements(
            manifest.get("requires")
        )
        if not supported:
            return item_from_plan(
                planned,
                collection_status="unsupported",
                reason=unsupported_reason,
                result={"kind": "table", "columns": [], "rows": [], "row_count": 0},
                diagnostics=[
                    {
                        "level": "warning",
                        "code": "unsupported_capability",
                        "failure_kind": "unsupported_capability",
                        "failure_kind_evidence": "manifest_requirements",
                        "message": unsupported_reason or "missing ClickHouse capability",
                    }
                ],
                source_text=sql,
                source_language="sql",
            )
        timeout = float(manifest.get("timeout_seconds", 0) or 0) or None
        execution = await adapter.execute_query(
            sql,
            target=target,
            timeout_seconds=timeout,
            optional_capability=bool(manifest.get("optional")),
        )
        _mark_declared_result_limit(manifest, execution)
        if manifest.get("sensitivity") == "sensitive":
            _sanitize_sensitive_result(execution.get("result") or {})
        return item_from_plan(
            planned,
            collection_status=str(execution["collection_status"]),
            reason=execution.get("reason"),
            timing_ms=execution.get("timing_ms"),
            result=execution["result"],
            diagnostics=execution.get("diagnostics"),
            source_text=execution.get("source_text"),
            source_language="sql",
        )
    if planned.source_kind == "script":
        if host_runner is None:
            return item_from_plan(
                planned,
                collection_status="skipped",
                reason="host collection is unavailable",
                result={"kind": "none"},
            )
        manifest = content.scripts[planned.source_id]
        source = render_host_script(
            load_host_script(content.path, manifest),
            runtime_context,
        )
        timeout = float(manifest.get("timeout_seconds", 2.0))
        started = time.perf_counter()
        try:
            result = await host_runner.run_script(source, timeout=timeout)
        except TimeoutError as exc:
            message = str(exc)
            return item_from_plan(
                planned,
                collection_status="timeout",
                reason=message,
                timing_ms=round((time.perf_counter() - started) * 1000, 3),
                result={"kind": "plain_text", "data": ""},
                diagnostics=[
                    {
                        "level": "error",
                        "code": "shell_timeout",
                        "failure_kind": "shell_timeout",
                        "failure_kind_evidence": "exception_type",
                        "message": message,
                    }
                ],
                source_text=source,
                source_language="bash",
            )
        status = "ok" if result.returncode == 0 else ("unsupported" if result.returncode == 3 else "error")
        reason = None if status == "ok" else (result.stderr.strip() or f"exit code {result.returncode}")
        diagnostics = []
        if result.stderr.strip():
            diagnostics.append(
                {"level": "warning" if status == "ok" else "error", "code": "stderr", "message": result.stderr[:4000]}
            )
        payload: dict[str, Any] = {"kind": "plain_text", "data": result.stdout}
        if status == "ok" and manifest.get("output") == "table_json":
            try:
                raw_rows = _parse_table_json_output(
                    result.stdout,
                    repair_legacy_lshw=planned.source_id.startswith("os.lshw_"),
                )
                names = list(dict.fromkeys(str(key) for row in raw_rows for key in row))
                columns = [
                    column_descriptor(name, _script_source_type(raw_rows, name), [], index)
                    for index, name in enumerate(names)
                ]
                _apply_script_column_contract(columns, manifest)
                payload = {
                    "kind": "table",
                    "columns": columns,
                    "rows": [[row.get(name) for name in names] for row in raw_rows],
                    "row_count": len(raw_rows),
                }
                if not raw_rows:
                    status = "empty"
            except ValueError as exc:
                status = "error"
                reason = f"invalid table_json output: {exc}"
                diagnostics.append({"level": "error", "code": "invalid_json", "message": reason})
                payload = {"kind": "plain_text", "data": result.stdout}
        return item_from_plan(
            planned,
            collection_status=status,
            reason=reason,
            timing_ms=round((time.perf_counter() - started) * 1000, 3),
            result=payload,
            diagnostics=diagnostics,
            source_text=source,
            source_language="bash",
        )
    return item_from_plan(
        planned,
        collection_status="skipped",
        reason="metric collection is unavailable in one-shot mode",
        result={"kind": "none"},
    )


def _mark_declared_result_limit(
    manifest: dict[str, Any],
    execution: dict[str, Any],
) -> None:
    """Conservatively expose a final SQL LIMIT as incomplete coverage."""

    row_limit = (manifest.get("result_contract") or {}).get("row_limit")
    result = execution.get("result") or {}
    row_count = result.get("row_count")
    if (
        not isinstance(row_limit, int)
        or isinstance(row_limit, bool)
        or execution.get("collection_status") not in {"ok", "empty"}
        or result.get("kind") != "table"
        or not isinstance(row_count, int)
        or row_count < row_limit
    ):
        return
    diagnostics = execution.setdefault("diagnostics", [])
    diagnostics.append(
        {
            "level": "warning",
            "code": "declared_result_limit_reached",
            "coverage_incomplete": True,
            "message": (
                f"Query returned the declared maximum of {row_limit} rows; "
                "additional matching rows may exist."
            ),
            "row_limit": row_limit,
        }
    )


def _parse_table_json_output(
    output: str,
    *,
    repair_legacy_lshw: bool,
) -> list[dict[str, Any]]:
    text = output.strip()
    if not text:
        return []
    try:
        decoded = json.loads(text)
    except json.JSONDecodeError as exc:
        if repair_legacy_lshw:
            try:
                decoded = _parse_legacy_lshw_json(text)
            except json.JSONDecodeError:
                pass
            else:
                return _json_record_rows(decoded)
        raise ValueError(f"invalid table_json output: {exc}") from exc
    return _json_record_rows(decoded)


def _json_record_rows(decoded: Any) -> list[dict[str, Any]]:
    rows = decoded if isinstance(decoded, list) else [decoded]
    if any(not isinstance(row, dict) for row in rows):
        raise ValueError("invalid table_json output: top-level JSON must contain objects")
    return rows


def _parse_legacy_lshw_json(text: str) -> Any:
    """Repair only the malformed filtered JSON emitted by lshw 02.18.x."""

    if text.strip() == "]":
        return []
    repaired = re.sub(r"}\s+{", "}}, {", text)
    repaired = re.sub(
        r'("(?:\\.|[^"\\])*"|-?\d+(?:\.\d+)?|true|false|null)\s+{',
        r"\1}, {",
        repaired,
    )
    repaired = re.sub(r"}\s*,\s*}\s*,\s*{", "}, {", repaired)
    repaired = re.sub(r",\s*}\s*]\s*$", "\n]", repaired)
    repaired = re.sub(r",\s*]\s*$", "\n]", repaired)
    repaired = _close_legacy_lshw_unterminated_object(repaired)
    return json.loads(repaired)


def _close_legacy_lshw_unterminated_object(text: str) -> str:
    if not text.lstrip().startswith("[") or not text.rstrip().endswith("]"):
        return text
    object_depth = 0
    in_string = False
    escaped = False
    for character in text:
        if in_string:
            if escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == '"':
                in_string = False
            continue
        if character == '"':
            in_string = True
        elif character == "{":
            object_depth += 1
        elif character == "}":
            object_depth -= 1
    if object_depth != 1:
        return text
    array_end = text.rfind("]")
    return text[:array_end] + "}\n" + text[array_end:]


def _script_source_type(rows: list[dict[str, Any]], name: str) -> str:
    value = next((row.get(name) for row in rows if row.get(name) is not None), None)
    if isinstance(value, bool):
        return "Bool"
    if isinstance(value, int):
        return "Int64"
    if isinstance(value, float):
        return "Float64"
    if isinstance(value, (dict, list)):
        return "JSON"
    return "String"


def _apply_script_column_contract(
    columns: list[dict[str, Any]],
    manifest: dict[str, Any],
) -> None:
    declared = (manifest.get("result_contract") or {}).get("columns") or {}
    if not isinstance(declared, dict):
        return
    allowed = {
        "label",
        "value_kind",
        "semantic_role",
        "quantity",
        "quantity_ref",
        "unit",
        "unit_ref",
        "quality",
        "nullable",
        "encoding",
    }
    for column in columns:
        override = declared.get(column.get("name"))
        if isinstance(override, dict):
            column.update({key: value for key, value in override.items() if key in allowed})


_SQL_LITERAL_RE = re.compile(r"'(?:''|\\.|[^'])*'")
_SQL_NUMBER_RE = re.compile(r"(?<![A-Za-z0-9_])[-+]?\d+(?:\.\d+)?(?![A-Za-z0-9_])")
_SECRET_VALUE_RE = re.compile(
    r"(?i)(password|passwd|secret|token|api[_-]?key)(\s*(?:=|:)\s*)([^\s,;]+)"
)


def _redact_exception(exc: BaseException) -> str:
    text = str(exc).replace("\x00", "").split("Stack trace:", 1)[0].rstrip()
    return _SECRET_VALUE_RE.sub(
        lambda match: match.group(1) + match.group(2) + "<redacted>",
        text,
    )[:4000]


def _sanitize_sensitive_result(result: dict[str, Any]) -> None:
    if result.get("kind") != "table":
        return
    columns = [str(column.get("name") or "").casefold() for column in result.get("columns") or []]
    for row in result.get("rows") or []:
        for index, column in enumerate(columns):
            if index >= len(row) or not isinstance(row[index], str):
                continue
            value = row[index].replace("\x00", "")
            if column in {"query", "_query", "query_text", "create_table_query"}:
                value = _SQL_LITERAL_RE.sub("'?'", value)
                value = _SQL_NUMBER_RE.sub("?", value)
                value = _SECRET_VALUE_RE.sub(
                    lambda match: match.group(1) + match.group(2) + "<redacted>",
                    value,
                )
                row[index] = value[:2000]
            elif any(token in column for token in ("exception", "error", "stack_trace")):
                row[index] = _SECRET_VALUE_RE.sub(
                    lambda match: match.group(1) + match.group(2) + "<redacted>",
                    value,
                )[:2000]


def _output_paths(
    out_dir: str | Path,
    target: DatabaseTarget,
    output_formats: set[str],
    *,
    json_out: str | Path | None,
    html_out: str | Path | None,
    multiple_targets: bool,
) -> tuple[Path | None, Path | None]:
    unknown = output_formats - {"json", "html"}
    if unknown:
        raise ValueError(f"unsupported output format(s): {', '.join(sorted(unknown))}")
    base = Path(out_dir).resolve()
    suffix = ""
    if target.scope == CLUSTER_SCOPE:
        safe_cluster = re.sub(r"[^A-Za-z0-9_.-]+", "_", target.cluster_name or "cluster")
        suffix = "_" + safe_cluster
    default_json = base / f"report{suffix}.json"
    default_html = base / f"report{suffix}.html"
    selected_json = Path(json_out).resolve() if json_out is not None else default_json
    selected_html = Path(html_out).resolve() if html_out is not None else default_html
    return (
        selected_json if "json" in output_formats else None,
        selected_html if "html" in output_formats else None,
    )
