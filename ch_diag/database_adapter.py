"""Product-neutral asynchronous database adapter contract.

The collector depends on this module instead of a concrete database driver.  A
database implementation owns connection/query cancellation and must release all
of its resources from :meth:`close`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable


@dataclass(frozen=True)
class DatabaseTarget:
    """A single execution target selected by a database adapter."""

    scope: str
    cluster_name: str | None = None


@runtime_checkable
class DatabaseConnectionConfig(Protocol):
    """Connection values and tunnel rebinding required by the lifecycle."""

    host: str
    port: int

    def tunneled(self, host: str, port: int) -> "DatabaseConnectionConfig": ...


@runtime_checkable
class DatabaseAdapter(Protocol):
    """Minimum database API used by planning, collection and snapshots."""

    async def detect_runtime_context(self) -> dict[str, Any]: ...

    async def resolve_targets(
        self,
        scope: str,
        selector: str | None,
    ) -> list[DatabaseTarget]: ...

    async def supports_requirements(
        self,
        requirements: dict[str, Any] | None,
    ) -> tuple[bool, str | None]: ...

    async def execute_query(
        self,
        sql: str,
        *,
        target: DatabaseTarget,
        timeout_seconds: float | None = None,
        optional_capability: bool = False,
    ) -> dict[str, Any]: ...

    async def close(self) -> None: ...


@runtime_checkable
class DatabaseAdapterFactory(Protocol):
    """Construct a product adapter from a neutral connection and runtime policy."""

    def __call__(
        self,
        connection: DatabaseConnectionConfig,
        runtime_policy: dict[str, Any],
    ) -> DatabaseAdapter: ...
