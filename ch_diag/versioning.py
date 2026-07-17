"""ClickHouse version parsing and declarative variant selection."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any, Iterable

_VERSION_RE = re.compile(r"^\s*(\d+)(?:\.(\d+))?(?:\.(\d+))?(?:\.(\d+))?")
_LTS_BRANCH_RE = re.compile(r"^[1-9]\d*\.(?:0|[1-9]\d*)$")


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

    @property
    def branch(self) -> str:
        """Return the release branch used by the LTS compatibility contract."""

        return f"{self.major}.{self.minor}"


def parse_lts_branch(value: str) -> ClickHouseVersion:
    """Parse an exact ``major.minor`` LTS branch declaration."""

    normalized = str(value).strip()
    if not _LTS_BRANCH_RE.fullmatch(normalized):
        raise ValueError(f"invalid ClickHouse LTS branch: {value!r}")
    return ClickHouseVersion.parse(normalized)


def resolve_lts_branch(
    version: ClickHouseVersion,
    supported_lts_versions: Iterable[str],
) -> str | None:
    """Resolve a server version to the nearest previously released LTS branch."""

    candidates = [
        (parse_lts_branch(str(branch)), str(branch))
        for branch in supported_lts_versions
    ]
    compatible = [entry for entry in candidates if entry[0] <= version]
    return max(compatible, default=(None, None), key=lambda entry: entry[0])[1]


def select_variant(
    variants: list[dict[str, Any]],
    version: ClickHouseVersion,
    scope: str,
    supported_lts_versions: Iterable[str] | None = None,
) -> dict[str, Any] | None:
    if supported_lts_versions is None:
        supported_lts_versions = sorted(
            {
                str(branch)
                for variant in variants
                for branch in variant.get("lts_versions") or []
            },
            key=parse_lts_branch,
        )
    compatibility_branch = resolve_lts_branch(version, supported_lts_versions)
    if compatibility_branch is None:
        return None
    matches = [
        variant
        for variant in variants
        if compatibility_branch in {str(branch) for branch in variant.get("lts_versions") or []}
        and scope in set(variant.get("scopes") or ["node", "cluster"])
    ]
    if len(matches) > 1:
        identifiers = ", ".join(str(item.get("id")) for item in matches)
        raise ValueError(
            f"overlapping query variants for {version}/{scope} via LTS "
            f"{compatibility_branch}: {identifiers}"
        )
    return matches[0] if matches else None
