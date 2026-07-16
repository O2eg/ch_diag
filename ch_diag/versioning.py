"""ClickHouse version parsing and declarative variant selection."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any, Iterable

_VERSION_RE = re.compile(r"^\s*(\d+)(?:\.(\d+))?(?:\.(\d+))?(?:\.(\d+))?")


@dataclass(frozen=True, order=True)
class ClickHouseVersion:
    major: int
    minor: int = 0
    patch: int = 0
    revision: int = 0

    @classmethod
    def parse(cls, value: str | int | Iterable[int] | "ClickHouseVersion") -> "ClickHouseVersion":
        if isinstance(value, cls):
            return value
        if isinstance(value, int):
            return cls(value)
        if not isinstance(value, str):
            parts = [int(part) for part in value]
            if not 1 <= len(parts) <= 4:
                raise ValueError(f"invalid ClickHouse version tuple: {parts!r}")
            return cls(*(parts + [0] * (4 - len(parts))))
        match = _VERSION_RE.match(value)
        if not match:
            raise ValueError(f"invalid ClickHouse version: {value!r}")
        parts = [int(part or 0) for part in match.groups()]
        return cls(*parts)

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}.{self.revision}"

    def as_list(self) -> list[int]:
        return [self.major, self.minor, self.patch, self.revision]


def variant_supports_version(variant: dict[str, Any], version: ClickHouseVersion) -> bool:
    minimum = ClickHouseVersion.parse(str(variant.get("min_ch_version", "0")))
    maximum_value = variant.get("max_ch_version")
    maximum = ClickHouseVersion.parse(str(maximum_value)) if maximum_value is not None else None
    return version >= minimum and (maximum is None or version < maximum)


def select_variant(
    variants: list[dict[str, Any]],
    version: ClickHouseVersion,
    scope: str,
) -> dict[str, Any] | None:
    matches = [
        variant
        for variant in variants
        if variant_supports_version(variant, version)
        and scope in set(variant.get("scopes") or ["node", "cluster"])
    ]
    if len(matches) > 1:
        identifiers = ", ".join(str(item.get("id")) for item in matches)
        raise ValueError(f"overlapping query variants for {version}/{scope}: {identifiers}")
    return matches[0] if matches else None
