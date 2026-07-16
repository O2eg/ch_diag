"""Strict, lossless JSON conversion shared by adapters and artifacts."""

from __future__ import annotations

from datetime import date, datetime, time
from decimal import Decimal
import math
from typing import Any
from uuid import UUID

SAFE_JSON_INTEGER = 9_007_199_254_740_991


def json_safe(value: Any, descriptor: dict[str, Any] | None = None) -> Any:
    if value is None or isinstance(value, (str, bool)):
        return value
    if isinstance(value, int):
        if descriptor and descriptor.get("encoding") == "decimal_string":
            return str(value)
        return value if abs(value) <= SAFE_JSON_INTEGER else str(value)
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, (datetime, date, time)):
        return value.isoformat()
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, bytes):
        try:
            return value.decode("utf-8")
        except UnicodeDecodeError:
            return value.hex()
    if isinstance(value, tuple):
        return [json_safe(item) for item in value]
    if isinstance(value, list):
        return [json_safe(item) for item in value]
    if isinstance(value, dict):
        return {str(key): json_safe(item) for key, item in value.items()}
    return str(value)
