"""Formal schema resources and fast built-in artifact field checks."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .errors import ChDiagError

SCHEMA_PATH = Path(__file__).resolve().parent / "schemas" / "artifact-v5.schema.json"
VALUE_KINDS = {"integer", "decimal", "timestamp", "date", "boolean", "json", "text"}
SEMANTIC_ROLES = {"gauge", "duration", "state", "label"}
QUALITIES = {"exact", "estimated", "derived"}
ENCODINGS = {"decimal_string", "json_string", "json_number", "json_boolean", "json_value"}
COLUMN_REQUIRED_FIELDS = {
    "name",
    "label",
    "source_type",
    "value_kind",
    "semantic_role",
    "quantity",
    "unit",
    "quality",
    "nullable",
    "encoding",
}


def load_artifact_schema() -> dict[str, Any]:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def validate_column_descriptor(column: dict[str, Any], *, location: str) -> None:
    missing = sorted(COLUMN_REQUIRED_FIELDS - set(column))
    if missing:
        raise ChDiagError(f"{location} misses column contract fields: {missing!r}")
    if not str(column.get("name") or ""):
        raise ChDiagError(f"{location} has an empty column name")
    for key, allowed in (
        ("value_kind", VALUE_KINDS),
        ("semantic_role", SEMANTIC_ROLES),
        ("quality", QUALITIES),
        ("encoding", ENCODINGS),
    ):
        if column.get(key) not in allowed:
            raise ChDiagError(f"{location} has invalid {key}={column.get(key)!r}")
    if not isinstance(column.get("nullable"), bool):
        raise ChDiagError(f"{location} nullable must be boolean")


def column_descriptor(
    name: str,
    source_type: str,
    rows: list[tuple[Any, ...]],
    index: int,
) -> dict[str, Any]:
    """Map a physical source type/name to the neutral schema-v5 column contract."""

    del rows, index  # Reserved for future value-based refinement.
    normalized = source_type.lower()
    nullable = normalized.startswith("nullable(")
    if any(token in normalized for token in ("int", "decimal")):
        value_kind = "integer" if "int" in normalized and "decimal" not in normalized else "decimal"
        encoding = "decimal_string" if value_kind == "integer" else "json_string"
        role, quantity, unit = "gauge", "count", "count"
    elif "float" in normalized:
        value_kind, encoding, role, quantity, unit = (
            "decimal",
            "json_number",
            "gauge",
            "count",
            "count",
        )
    elif "datetime" in normalized:
        value_kind, encoding, role, quantity, unit = (
            "timestamp",
            "json_string",
            "state",
            "timestamp",
            "none",
        )
    elif normalized == "date" or normalized.startswith("date"):
        value_kind, encoding, role, quantity, unit = (
            "date",
            "json_string",
            "state",
            "date",
            "none",
        )
    elif normalized in {"bool", "boolean"}:
        value_kind, encoding, role, quantity, unit = (
            "boolean",
            "json_boolean",
            "state",
            "boolean",
            "none",
        )
    elif any(token in normalized for token in ("array", "map", "tuple", "object", "json")):
        value_kind, encoding, role, quantity, unit = (
            "json",
            "json_value",
            "state",
            "structured",
            "none",
        )
    else:
        value_kind, encoding, role, quantity, unit = (
            "text",
            "json_string",
            "label",
            "identifier",
            "none",
        )
    lower_name = name.casefold()
    if lower_name.endswith("_bytes") or "bytes_on_disk" in lower_name or "memory_usage" in lower_name:
        quantity, unit = "data_volume", "bytes"
    elif lower_name.endswith("_ms") or "duration_ms" in lower_name:
        quantity, unit, role = "milliseconds", "ms", "duration"
    elif lower_name.endswith("_seconds") or lower_name in {"elapsed", "uptime"}:
        quantity, unit, role = "seconds", "s", "duration"
    elif lower_name.endswith("_pct") or lower_name.endswith("_percent"):
        quantity, unit = "percentage", "%"
    return {
        "name": str(name),
        "label": str(name).replace("_", " ").strip().title(),
        "source_type": source_type,
        "value_kind": value_kind,
        "semantic_role": role,
        "quantity": quantity,
        "unit": unit,
        "quality": "exact",
        "nullable": nullable,
        "encoding": encoding,
    }
