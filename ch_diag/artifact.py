"""Schema-version-5 diagnostic artifact construction and secure output."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import getpass
import json
import os
from pathlib import Path
import platform
import socket
import tempfile
from typing import Any

from . import __version__
from .artifact_schema import validate_column_descriptor
from .content_loader import ContentPack
from .database_adapter import DatabaseTarget
from .errors import ChDiagError
from .planner import ExecutionPlan, PlannedItem
from .runtime_config import ARTIFACT_SCHEMA_VERSION, CONTENT_SCHEMA_VERSION, DEFAULT_MAX_ARTIFACT_BYTES
from .serialization import json_safe

COLLECTION_STATUSES = {
    "ok",
    "empty",
    "error",
    "unsupported",
    "permission_denied",
    "timeout",
    "skipped",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def create_artifact(
    content: ContentPack,
    plan: ExecutionPlan,
    runtime_context: dict[str, Any],
    target: DatabaseTarget,
    *,
    started_at: str,
) -> dict[str, Any]:
    runtime = {
        "mode": plan.mode,
        "collection_mode": plan.collection_mode,
        "target_scope": target.scope,
        "sql_compatibility_lts": plan.compatibility_lts_version,
        "cluster_name": target.cluster_name,
        "collector_host": socket.gethostname(),
        "collector_user": getpass.getuser(),
        "collector_platform": platform.platform(),
        "started_at": started_at,
        "finished_at": None,
        **json_safe(runtime_context),
    }
    return {
        "artifact_schema_version": ARTIFACT_SCHEMA_VERSION,
        "generator": {"name": "ch_diag", "product": "ch_diag", "version": __version__},
        "content": {
            "schema_version": CONTENT_SCHEMA_VERSION,
            "content_path": str(content.path),
            "checksum": content.checksum,
            "report_id": content.report["report"]["id"],
            "document": json_safe(content.document),
            "provenance": json_safe(content.provenance),
        },
        "report": {
            "id": content.report["report"]["id"],
            "title": content.report["report"]["title"],
            "description": content.report["report"].get("description"),
        },
        "database": {
            "engine": "clickhouse",
            "server_version": runtime_context.get("server_version"),
            "sql_compatibility_lts": plan.compatibility_lts_version,
        },
        "target": {
            "execution_scope": target.scope,
            "cluster_name": target.cluster_name,
            "connection_endpoint": {
                "host": runtime_context.get("database_host_ip"),
                "port": runtime_context.get("database_port"),
            },
            "host_scope": (
                "ssh_target" if plan.collection_mode == "remote" else "collector"
            ),
        },
        "runtime": runtime,
        "display": json_safe(content.report.get("defaults") or {}),
        "sections": deepcopy(plan.sections),
        "items": {},
        "query_texts": {},
        "snapshot_schemas": {},
        "snapshots": [],
        "diagnostics": [],
    }


def item_from_plan(
    planned: PlannedItem,
    *,
    collection_status: str,
    result: dict[str, Any],
    reason: str | None = None,
    timing_ms: float | None = None,
    diagnostics: list[dict[str, Any]] | None = None,
    source_text: str | None = None,
    source_language: str | None = None,
) -> dict[str, Any]:
    metadata = deepcopy(planned.source_metadata)
    if source_text is not None:
        metadata["source_text"] = source_text
    if source_language is not None:
        metadata["source_language"] = source_language
    return {
        "item_id": planned.item_id,
        "section_id": planned.section_id,
        "item_key": planned.item_key,
        "title": planned.title,
        "source_kind": planned.source_kind,
        "source_id": planned.source_id,
        "state": planned.state,
        "collection_status": collection_status,
        "severity_level": "unknown" if collection_status not in {"ok", "empty"} else "ok",
        "reason": reason,
        "collected_at": utc_now(),
        "timing_ms": timing_ms,
        "result": json_safe(result),
        "source_metadata": json_safe(metadata),
        "issues": {},
        "diagnostics": json_safe(diagnostics or []),
    }


def strip_artifact_metadata(artifact: dict[str, Any]) -> dict[str, Any]:
    artifact["runtime"]["strip_meta"] = True
    for item in artifact.get("items", {}).values():
        metadata = item.get("source_metadata") or {}
        item["source_metadata"] = {
            key: deepcopy(metadata[key])
            for key in ("tags", "execution_scope", "chart", "render", "display")
            if key in metadata
        }
    document = artifact["content"]["document"]
    presentation = ((document.get("catalogs") or {}).get("presentation") or {})
    artifact["content"]["document"] = {
        "report": deepcopy(document.get("report") or {}),
        "runtime_policy": {},
        "defaults": deepcopy(document.get("defaults") or {}),
        "sections": {},
        "catalogs": {
            "queries": {},
            "scripts": {},
            "metrics": {},
            "python": {},
            "presentation": deepcopy(presentation),
        },
        "queries": {},
        "scripts": {},
        "metrics": {},
        "python_sources": {},
        "sampler_providers": {},
        "instructions": {},
        "field_reference": {},
    }
    artifact["content"]["provenance"] = {"report": ["report.yaml"]}
    artifact["query_texts"] = {}
    return artifact


def omit_uncollected_items(artifact: dict[str, Any], omitted: set[str]) -> None:
    for item_id in omitted:
        artifact["items"].pop(item_id, None)
    retained_sections = []
    for section in artifact["sections"]:
        section["items"] = [item_id for item_id in section["items"] if item_id not in omitted]
        if section["items"]:
            retained_sections.append(section)
    artifact["sections"] = retained_sections


def validate_artifact(artifact: dict[str, Any]) -> None:
    if artifact.get("artifact_schema_version") != ARTIFACT_SCHEMA_VERSION:
        raise ChDiagError("unsupported artifact schema version")
    required = {
        "generator",
        "content",
        "report",
        "database",
        "target",
        "runtime",
        "display",
        "sections",
        "items",
        "query_texts",
        "snapshot_schemas",
        "snapshots",
        "diagnostics",
    }
    missing = sorted(required - set(artifact))
    if missing:
        raise ChDiagError(f"artifact misses required fields: {missing!r}")
    item_ids = set(artifact["items"])
    referenced: set[str] = set()
    for section in artifact["sections"]:
        for item_id in section.get("items") or []:
            if item_id in referenced:
                raise ChDiagError(f"artifact item {item_id!r} belongs to multiple sections")
            referenced.add(item_id)
    if referenced != item_ids:
        raise ChDiagError("artifact section/item references are inconsistent")
    for item_id, item in artifact["items"].items():
        status = item.get("collection_status")
        if status not in COLLECTION_STATUSES:
            raise ChDiagError(f"artifact item {item_id!r} has invalid status {status!r}")
        result = item.get("result") or {}
        if result.get("kind") not in {"table", "plain_text", "chart", "none"}:
            raise ChDiagError(f"artifact item {item_id!r} has invalid result kind")
        if result.get("kind") == "table":
            columns = result.get("columns") or []
            rows = result.get("rows") or []
            for index, column in enumerate(columns):
                if not isinstance(column, dict):
                    raise ChDiagError(
                        f"artifact item {item_id!r} column {index} is not an object"
                    )
                validate_column_descriptor(
                    column,
                    location=f"artifact item {item_id!r} column {index}",
                )
            if any(len(row) != len(columns) for row in rows):
                raise ChDiagError(f"artifact item {item_id!r} has malformed table rows")
            if result.get("row_count") != len(rows):
                raise ChDiagError(f"artifact item {item_id!r} has inconsistent row_count")
        if result.get("kind") == "chart":
            series = result.get("series") or []
            if result.get("series_count") != len(series):
                raise ChDiagError(
                    f"artifact item {item_id!r} has inconsistent series_count"
                )
    try:
        json.dumps(artifact, ensure_ascii=False, allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise ChDiagError(f"artifact is not strict JSON: {exc}") from exc


def write_text_secure(path: str | Path, text: str, *, max_bytes: int | None = None) -> None:
    destination = Path(os.path.abspath(Path(path).expanduser()))
    destination.parent.mkdir(parents=True, exist_ok=True)
    encoded = text.encode("utf-8")
    if max_bytes is not None and len(encoded) > max_bytes:
        raise ChDiagError(
            f"output {destination} is {len(encoded)} bytes, above limit {max_bytes}"
        )
    descriptor, temporary_name = tempfile.mkstemp(
        prefix="." + destination.name + ".",
        dir=str(destination.parent),
    )
    temporary = Path(temporary_name)
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, destination)
        os.chmod(destination, 0o600)
    except BaseException:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass
        raise


def write_json(
    path: str | Path,
    artifact: dict[str, Any],
    *,
    max_bytes: int = DEFAULT_MAX_ARTIFACT_BYTES,
) -> None:
    validate_artifact(artifact)
    text = json.dumps(artifact, ensure_ascii=False, allow_nan=False, indent=2) + "\n"
    write_text_secure(path, text, max_bytes=max_bytes)
