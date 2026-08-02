"""Stable machine contract and deterministic artifact inspection for ch_diag."""

from __future__ import annotations

from collections import Counter
import hashlib
import json
from pathlib import Path
from typing import Any

from . import __version__
from .artifact import FAILED_COLLECTION_STATUSES, SUCCESSFUL_COLLECTION_STATUSES, validate_artifact
from .errors import ChDiagError
from .runtime_config import (
    ARTIFACT_SCHEMA_VERSION,
    COLLECTION_MODES,
    CONTENT_SCHEMA_VERSION,
    TARGET_SCOPES,
)

CONTRACT_VERSION = "ch_play/component/v1"
CAPABILITY_SCHEMA_VERSION = "ch_play/capabilities/v1"
COMPONENT = "ch_diag"
MACHINE_INTERFACE = {
    "machine_flag": "--machine",
    "request_id_option": "--request-id",
    "capabilities_option": "--component-capabilities",
}

EXIT_CODES = {
    "success": 0,
    "validation_error": 2,
    "precondition_failed": 3,
    "unsupported": 4,
    "partial": 5,
    "execution_error": 6,
    "cancelled": 7,
    "ownership_error": 8,
}


def canonical_hash(value: Any) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def file_hash(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return "sha256:" + digest.hexdigest()


def load_artifact(path: str | Path) -> dict[str, Any]:
    artifact_path = Path(path).expanduser().resolve()
    try:
        document = json.loads(artifact_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ChDiagError(f"cannot read report artifact {artifact_path}: {exc}") from exc
    if not isinstance(document, dict):
        raise ChDiagError("report artifact root must be a JSON object")
    validate_artifact(document)
    return document


def summarize_artifact(artifact: dict[str, Any]) -> dict[str, Any]:
    validate_artifact(artifact)
    items = artifact.get("items") or {}
    collection_statuses = Counter(
        str(item.get("collection_status", "unknown")) for item in items.values()
    )
    severity_levels = Counter(
        str(item.get("severity_level", "unknown")) for item in items.values()
    )
    fallback_item_ids: list[str] = []
    fallback_triggers: Counter[str] = Counter()
    fallback_statuses: Counter[str] = Counter()
    item_diagnostic_count = 0
    for item_id, item in items.items():
        item_diagnostic_count += len(item.get("diagnostics") or [])
        fallback = ((item.get("source_metadata") or {}).get("fallback") or {})
        if not isinstance(fallback, dict) or fallback.get("used") is not True:
            continue
        fallback_item_ids.append(str(item_id))
        fallback_triggers[str(fallback.get("trigger") or "unknown")] += 1
        fallback_statuses[str(item.get("collection_status") or "unknown")] += 1
    fallback_item_ids.sort()
    total = len(items)
    successful = sum(
        collection_statuses.get(status, 0) for status in SUCCESSFUL_COLLECTION_STATUSES
    )
    failed = sum(collection_statuses.get(status, 0) for status in FAILED_COLLECTION_STATUSES)
    runtime = artifact.get("runtime") or {}
    collection_summary = runtime.get("collection_summary") or {}
    complete = collection_summary.get("complete_items")
    if not isinstance(complete, int):
        complete = successful
    snapshots = artifact.get("snapshots") or []
    snapshot_count = len(snapshots) if isinstance(snapshots, list) else 0
    return {
        "schema_version": "ch_diag/summary-v1",
        "artifact_schema_version": artifact.get("artifact_schema_version"),
        "artifact_hash": canonical_hash(artifact),
        "generator": artifact.get("generator"),
        "report": artifact.get("report"),
        "runtime": runtime,
        "content": {
            "checksum": (artifact.get("content") or {}).get("checksum"),
            "report_id": (artifact.get("content") or {}).get("report_id"),
        },
        "section_count": len(artifact.get("sections") or []),
        "item_count": total,
        "snapshot_count": snapshot_count,
        "collection_statuses": dict(sorted(collection_statuses.items())),
        "severity_levels": dict(sorted(severity_levels.items())),
        "diagnostic_count": len(artifact.get("diagnostics") or []) + item_diagnostic_count,
        "completeness": {
            "successful_items": successful,
            "complete_items": complete,
            "failed_items": failed,
            "total_items": total,
            "ratio": round(complete / total, 6) if total else 1.0,
        },
        "fallback_items": {
            "count": len(fallback_item_ids),
            "item_ids": fallback_item_ids,
            "triggers": dict(sorted(fallback_triggers.items())),
            "collection_statuses": dict(sorted(fallback_statuses.items())),
        },
        "degraded": bool(runtime.get("degraded") or fallback_item_ids),
        "has_errors": bool(failed),
    }


def summarize_execution_plan(plan: dict[str, Any]) -> dict[str, Any]:
    items = plan.get("items") or []
    if not isinstance(items, list):
        items = []
    status_counts = Counter(str(item.get("status", "unknown")) for item in items)
    target_counts: Counter[str] = Counter()
    fallback_count = 0
    item_ids: list[str] = []
    for item in items:
        if item.get("item_id"):
            item_ids.append(str(item["item_id"]))
        for target in item.get("targets") or []:
            target_counts[str(target)] += 1
        fallback_count += item.get("fallback_item") is not None
    item_ids.sort()
    return {
        "schema_version": "ch_diag/plan-summary-v1",
        "plan_hash": canonical_hash(plan),
        "server_version": plan.get("server_version"),
        "sql_compatibility_lts": plan.get("sql_compatibility_lts"),
        "mode": plan.get("mode"),
        "collection_mode": plan.get("collection_mode"),
        "target_scope": plan.get("target_scope"),
        "item_count": len(items),
        "status_counts": dict(sorted(status_counts.items())),
        "target_counts": dict(sorted(target_counts.items())),
        "fallback_item_count": fallback_count,
        "item_ids_hash": canonical_hash(item_ids),
    }


def capabilities() -> dict[str, Any]:
    command_names = (
        "capabilities",
        "validate",
        "explain-plan",
        "one-shot",
        "snapshots",
        "validate-artifact",
        "summarize",
        "render",
    )
    return {
        "capability_schema_version": CAPABILITY_SCHEMA_VERSION,
        "machine_interface": MACHINE_INTERFACE,
        "contract_version": CONTRACT_VERSION,
        "component": COMPONENT,
        "component_version": __version__,
        "commands": {
            name: {
                "mutates_target": False,
                "machine_output": True,
                "accepts_plan_hash": False,
            }
            for name in command_names
        },
        "artifact_schema_versions": [ARTIFACT_SCHEMA_VERSION],
        "summary_schema_versions": ["ch_diag/summary-v1"],
        "plan_summary_schema_versions": ["ch_diag/plan-summary-v1"],
        "content_schema_versions": [CONTENT_SCHEMA_VERSION],
        "collection_modes": sorted(COLLECTION_MODES),
        "target_scopes": sorted(TARGET_SCOPES),
        "exit_codes": EXIT_CODES,
        "secret_policy": {
            "password_sources": ["argument", "environment", "prompt"],
            "errors_are_redacted": True,
            "machine_output_contains_secrets": False,
        },
    }


def artifact_descriptor(
    path: str | Path,
    *,
    kind: str,
    schema_version: str | int | None,
) -> dict[str, Any]:
    resolved = Path(path).expanduser().resolve()
    return {
        "kind": kind,
        "schema_version": schema_version,
        "path": str(resolved),
        "hash": file_hash(resolved),
        "size_bytes": resolved.stat().st_size,
    }


def envelope(
    command: str,
    status: str,
    *,
    request_id: str | None,
    result: Any = None,
    artifacts: list[dict[str, Any]] | None = None,
    warnings: list[str] | None = None,
    error: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "contract_version": CONTRACT_VERSION,
        "component": COMPONENT,
        "component_version": __version__,
        "command": command,
        "request_id": request_id,
        "status": status,
        "result": result,
        "artifacts": artifacts or [],
        "warnings": warnings or [],
        "error": error,
    }
