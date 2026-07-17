"""Strict TOML configuration for the report-review harness."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = Path(__file__).with_name("review.toml")


@dataclass(frozen=True)
class FixtureConfig:
    manage: bool
    build: bool
    seed: bool
    cleanup: bool
    compose_file: Path
    compose_overlay: Path
    project_name: str
    keeper_container: str
    node1_container: str
    node2_container: str
    keeper_port: int
    node1_port: int
    node2_port: int
    node1_ssh_port: int
    node2_ssh_port: int
    startup_timeout_seconds: float
    state_directory: Path


@dataclass(frozen=True)
class DatabaseConfig:
    host: str
    port: int
    database: str
    user: str
    password_env: str
    cluster_name: str


@dataclass(frozen=True)
class SSHConfig:
    host: str
    port: int
    user: str
    key: Path
    known_hosts: Path


@dataclass(frozen=True)
class MatrixConfig:
    modes: tuple[str, ...]
    scopes: tuple[str, ...]
    run_types: tuple[str, ...]
    formats: tuple[str, ...]
    output_root: Path
    snapshot_duration_seconds: float
    snapshot_interval_seconds: float
    snapshot_tags: tuple[str, ...]
    strict_collection: bool


@dataclass(frozen=True)
class WorkloadConfig:
    enabled: bool
    database: str
    seed_rows: int
    insert_rows_per_batch: int
    interval_seconds: float
    cpu_numbers_per_query: int
    failed_query_every: int


@dataclass(frozen=True)
class RuntimeConfig:
    ch_diag_executable: Path
    browser_validation: bool
    browser_executable: str | None
    browser_timeout_seconds: float


@dataclass(frozen=True)
class ReviewConfig:
    source: Path
    fixture: FixtureConfig
    database: DatabaseConfig
    ssh: SSHConfig
    matrix: MatrixConfig
    workload: WorkloadConfig
    runtime: RuntimeConfig


SECTIONS: dict[str, set[str]] = {
    "fixture": {
        "manage",
        "build",
        "seed",
        "cleanup",
        "compose_file",
        "compose_overlay",
        "project_name",
        "keeper_container",
        "node1_container",
        "node2_container",
        "keeper_port",
        "node1_port",
        "node2_port",
        "node1_ssh_port",
        "node2_ssh_port",
        "startup_timeout_seconds",
        "state_directory",
    },
    "database": {"host", "port", "database", "user", "password_env", "cluster_name"},
    "ssh": {"host", "port", "user", "key", "known_hosts"},
    "matrix": {
        "modes",
        "scopes",
        "run_types",
        "formats",
        "output_root",
        "snapshot_duration_seconds",
        "snapshot_interval_seconds",
        "snapshot_tags",
        "strict_collection",
    },
    "workload": {
        "enabled",
        "database",
        "seed_rows",
        "insert_rows_per_batch",
        "interval_seconds",
        "cpu_numbers_per_query",
        "failed_query_every",
    },
    "runtime": {
        "ch_diag_executable",
        "browser_validation",
        "browser_executable",
        "browser_timeout_seconds",
    },
}


def _load_toml(path: Path) -> dict[str, Any]:
    try:
        import tomllib
    except ModuleNotFoundError:  # pragma: no cover - Python 3.10
        import tomli as tomllib  # type: ignore[no-redef]
    with path.open("rb") as stream:
        document = tomllib.load(stream)
    if not isinstance(document, dict):
        raise ValueError("review configuration must be a TOML document")
    return document


def _path(value: Any, label: str) -> Path:
    path = Path(str(value)).expanduser()
    if not path.is_absolute():
        path = ROOT / path
    return path.resolve()


def _table(document: dict[str, Any], name: str) -> dict[str, Any]:
    value = document.get(name)
    if not isinstance(value, dict):
        raise ValueError(f"missing or invalid [{name}] table")
    unknown = sorted(set(value) - SECTIONS[name])
    if unknown:
        raise ValueError(f"unknown key(s) in [{name}]: {', '.join(unknown)}")
    return value


def _string(value: Any, label: str) -> str:
    result = str(value).strip()
    if not result:
        raise ValueError(f"{label} must not be empty")
    return result


def _port(value: Any, label: str) -> int:
    result = int(value)
    if not 1 <= result <= 65535:
        raise ValueError(f"{label} must be between 1 and 65535")
    return result


def _float(value: Any, label: str, *, minimum: float = 0.0) -> float:
    result = float(value)
    if result <= minimum:
        raise ValueError(f"{label} must be greater than {minimum}")
    return result


def _positive_int(value: Any, label: str, *, minimum: int = 1) -> int:
    result = int(value)
    if result < minimum:
        raise ValueError(f"{label} must be greater than or equal to {minimum}")
    return result


def _strings(value: Any, label: str, *, allow_empty: bool = False) -> tuple[str, ...]:
    if not isinstance(value, list) or (not value and not allow_empty):
        qualifier = "a TOML array" if allow_empty else "a non-empty TOML array"
        raise ValueError(f"{label} must be {qualifier}")
    result = tuple(_string(item, label) for item in value)
    if len(result) != len(set(result)):
        raise ValueError(f"{label} contains duplicate values")
    return result


def _choice_list(value: Any, label: str, allowed: set[str]) -> tuple[str, ...]:
    result = _strings(value, label)
    invalid = sorted(set(result) - allowed)
    if invalid:
        raise ValueError(f"{label} contains invalid value(s): {', '.join(invalid)}")
    return result


def load_review_config(path: str | Path | None = None) -> ReviewConfig:
    source = Path(path or DEFAULT_CONFIG).expanduser().resolve()
    if not source.is_file():
        raise ValueError(f"review configuration does not exist: {source}")
    document = _load_toml(source)
    unknown_sections = sorted(set(document) - set(SECTIONS))
    if unknown_sections:
        raise ValueError("unknown review section(s): " + ", ".join(unknown_sections))

    fixture = _table(document, "fixture")
    database = _table(document, "database")
    ssh = _table(document, "ssh")
    matrix = _table(document, "matrix")
    workload = _table(document, "workload")
    runtime = _table(document, "runtime")

    fixture_config = FixtureConfig(
        manage=bool(fixture["manage"]),
        build=bool(fixture["build"]),
        seed=bool(fixture["seed"]),
        cleanup=bool(fixture["cleanup"]),
        compose_file=_path(fixture["compose_file"], "fixture.compose_file"),
        compose_overlay=_path(fixture["compose_overlay"], "fixture.compose_overlay"),
        project_name=_string(fixture["project_name"], "fixture.project_name"),
        keeper_container=_string(fixture["keeper_container"], "fixture.keeper_container"),
        node1_container=_string(fixture["node1_container"], "fixture.node1_container"),
        node2_container=_string(fixture["node2_container"], "fixture.node2_container"),
        keeper_port=_port(fixture["keeper_port"], "fixture.keeper_port"),
        node1_port=_port(fixture["node1_port"], "fixture.node1_port"),
        node2_port=_port(fixture["node2_port"], "fixture.node2_port"),
        node1_ssh_port=_port(fixture["node1_ssh_port"], "fixture.node1_ssh_port"),
        node2_ssh_port=_port(fixture["node2_ssh_port"], "fixture.node2_ssh_port"),
        startup_timeout_seconds=_float(
            fixture["startup_timeout_seconds"], "fixture.startup_timeout_seconds"
        ),
        state_directory=_path(fixture["state_directory"], "fixture.state_directory"),
    )
    database_config = DatabaseConfig(
        host=_string(database["host"], "database.host"),
        port=_port(database["port"], "database.port"),
        database=_string(database["database"], "database.database"),
        user=_string(database["user"], "database.user"),
        password_env=_string(database["password_env"], "database.password_env"),
        cluster_name=_string(database["cluster_name"], "database.cluster_name"),
    )
    ssh_config = SSHConfig(
        host=_string(ssh["host"], "ssh.host"),
        port=_port(ssh["port"], "ssh.port"),
        user=_string(ssh["user"], "ssh.user"),
        key=_path(ssh["key"], "ssh.key"),
        known_hosts=_path(ssh["known_hosts"], "ssh.known_hosts"),
    )
    matrix_config = MatrixConfig(
        modes=_choice_list(
            matrix["modes"],
            "matrix.modes",
            {"local", "remote", "remote-db-only"},
        ),
        scopes=_choice_list(matrix["scopes"], "matrix.scopes", {"node", "cluster"}),
        run_types=_choice_list(
            matrix["run_types"], "matrix.run_types", {"one-shot", "snapshots"}
        ),
        formats=_choice_list(matrix["formats"], "matrix.formats", {"html", "json"}),
        output_root=_path(matrix["output_root"], "matrix.output_root"),
        snapshot_duration_seconds=_float(
            matrix["snapshot_duration_seconds"], "matrix.snapshot_duration_seconds"
        ),
        snapshot_interval_seconds=_float(
            matrix["snapshot_interval_seconds"], "matrix.snapshot_interval_seconds"
        ),
        snapshot_tags=_strings(
            matrix["snapshot_tags"], "matrix.snapshot_tags", allow_empty=True
        ),
        strict_collection=bool(matrix["strict_collection"]),
    )
    if matrix_config.snapshot_duration_seconds < matrix_config.snapshot_interval_seconds:
        raise ValueError("snapshot duration must be greater than or equal to interval")
    if set(matrix_config.formats) != {"html", "json"}:
        raise ValueError("review matrix requires both html and json formats")
    workload_config = WorkloadConfig(
        enabled=bool(workload["enabled"]),
        database=_string(workload["database"], "workload.database"),
        seed_rows=_positive_int(workload["seed_rows"], "workload.seed_rows"),
        insert_rows_per_batch=_positive_int(
            workload["insert_rows_per_batch"], "workload.insert_rows_per_batch"
        ),
        interval_seconds=_float(
            workload["interval_seconds"], "workload.interval_seconds"
        ),
        cpu_numbers_per_query=_positive_int(
            workload["cpu_numbers_per_query"], "workload.cpu_numbers_per_query"
        ),
        failed_query_every=_positive_int(
            workload["failed_query_every"], "workload.failed_query_every"
        ),
    )
    runtime_config = RuntimeConfig(
        ch_diag_executable=_path(runtime["ch_diag_executable"], "runtime.ch_diag_executable"),
        browser_validation=bool(runtime["browser_validation"]),
        browser_executable=(
            _string(runtime["browser_executable"], "runtime.browser_executable")
            if runtime.get("browser_executable")
            else None
        ),
        browser_timeout_seconds=_float(
            runtime["browser_timeout_seconds"], "runtime.browser_timeout_seconds"
        ),
    )
    return ReviewConfig(
        source=source,
        fixture=fixture_config,
        database=database_config,
        ssh=ssh_config,
        matrix=matrix_config,
        workload=workload_config,
        runtime=runtime_config,
    )
