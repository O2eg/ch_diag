"""Load and verify the autonomous ch_diag declarative content pack."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
import hashlib
from pathlib import Path
from typing import Any, Iterator

import yaml

from .errors import ContentIntegrityError, ContentValidationError
from .runtime_config import CONTENT_SCHEMA_VERSION, EXECUTABLE_CONTENT_SUFFIXES, INTEGRITY_FILE
from .versioning import ClickHouseVersion


class UniqueKeySafeLoader(yaml.SafeLoader):
    pass


def _construct_mapping(loader: UniqueKeySafeLoader, node: yaml.nodes.MappingNode, deep: bool = False):
    result: dict[Any, Any] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in result:
            raise ContentValidationError(f"duplicate YAML key {key!r} at line {key_node.start_mark.line + 1}")
        result[key] = loader.construct_object(value_node, deep=deep)
    return result


UniqueKeySafeLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    _construct_mapping,
)


@dataclass(frozen=True)
class ContentPack:
    path: Path
    report: dict[str, Any]
    queries: dict[str, dict[str, Any]]
    scripts: dict[str, dict[str, Any]]
    metrics: dict[str, dict[str, Any]]
    sampler_providers: dict[str, dict[str, Any]]
    instructions: dict[str, str]
    document: dict[str, Any]
    provenance: dict[str, list[str]]
    checksum: str


def default_content_path() -> Path:
    return Path(__file__).resolve().parent / "content"


def protected_content_files(root: Path) -> list[Path]:
    return sorted(
        path
        for path in root.rglob("*")
        if path.is_file()
        and path.name != INTEGRITY_FILE
        and path.suffix.lower() in EXECUTABLE_CONTENT_SUFFIXES
        and "__pycache__" not in path.parts
    )


def content_file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def build_integrity_manifest(root: str | Path) -> str:
    base = Path(root).resolve()
    lines = [
        f"{content_file_hash(path)}  {path.relative_to(base).as_posix()}"
        for path in protected_content_files(base)
    ]
    return "\n".join(lines) + "\n"


def verify_content_integrity(root: str | Path) -> str:
    base = Path(root).resolve()
    manifest_path = base / INTEGRITY_FILE
    if not manifest_path.is_file():
        raise ContentIntegrityError(
            "Vendor content integrity baseline is missing; collection is disabled"
        )
    expected_lines = manifest_path.read_text(encoding="utf-8").splitlines()
    expected: dict[str, str] = {}
    for line_number, raw in enumerate(expected_lines, 1):
        line = raw.strip()
        if not line:
            continue
        parts = line.split(None, 1)
        if len(parts) != 2 or len(parts[0]) != 64:
            raise ContentIntegrityError(f"invalid integrity baseline line {line_number}")
        relative = parts[1].strip()
        if relative.startswith("*"):
            relative = relative[1:]
        if relative.startswith("/") or ".." in Path(relative).parts:
            raise ContentIntegrityError(f"unsafe integrity path at line {line_number}")
        if relative in expected:
            raise ContentIntegrityError(f"duplicate integrity path {relative!r}")
        expected[relative] = parts[0].lower()

    actual_files = protected_content_files(base)
    actual_paths = {path.relative_to(base).as_posix() for path in actual_files}
    if set(expected) != actual_paths:
        raise ContentIntegrityError(
            "Vendor content differs from the packaged baseline; collection is disabled. "
            "Restore ch_diag from a trusted distribution before running checks"
        )
    for path in actual_files:
        relative = path.relative_to(base).as_posix()
        if content_file_hash(path) != expected[relative]:
            raise ContentIntegrityError(
                "Vendor content differs from the packaged baseline; collection is disabled. "
                "Restore ch_diag from a trusted distribution before running checks"
            )
    digest = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
    return "sha256:" + digest


def _load_yaml(path: Path) -> dict[str, Any]:
    try:
        value = yaml.load(path.read_text(encoding="utf-8"), Loader=UniqueKeySafeLoader)
    except (OSError, yaml.YAMLError) as exc:
        raise ContentValidationError(f"cannot load {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ContentValidationError(f"{path} must contain a YAML mapping")
    return value


def _safe_path(root: Path, relative: str, label: str) -> Path:
    candidate = (root / relative).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise ContentValidationError(f"{label} escapes content root: {relative!r}") from exc
    return candidate


def load_content(content_path: str | Path | None = None) -> ContentPack:
    root = Path(content_path or default_content_path()).resolve()
    checksum = verify_content_integrity(root)
    report = _load_yaml(root / "report.yaml")
    query_catalog = _load_yaml(root / "queries.yaml")
    script_catalog = _load_yaml(root / "scripts.yaml")
    metric_catalog = _load_yaml(root / "metrics.yaml")

    queries = _mapping(query_catalog.get("queries"), "queries.yaml:queries")
    scripts = _mapping(script_catalog.get("scripts"), "scripts.yaml:scripts")
    metrics = _mapping(metric_catalog.get("metrics"), "metrics.yaml:metrics")
    sampler_providers = _mapping(
        metric_catalog.get("sampler_providers"),
        "metrics.yaml:sampler_providers",
    )
    instructions: dict[str, str] = {}
    provenance: dict[str, list[str]] = {
        "report": ["report.yaml"],
        "catalogs/queries": ["queries.yaml"],
        "catalogs/scripts": ["scripts.yaml"],
        "catalogs/metrics": ["metrics.yaml"],
    }
    for _section_id, _item_key, item_id, item in iter_report_items_from_report(report):
        ref = item.get("instruction") or f"instructions/items/{item_id.replace('.', '/')}.md"
        instruction_path = _safe_path(root, str(ref), f"instruction for {item_id}")
        if instruction_path.is_file():
            instructions[item_id] = instruction_path.read_text(encoding="utf-8")
            provenance[f"instructions/{item_id}"] = [instruction_path.relative_to(root).as_posix()]

    document = {
        "report": deepcopy(_mapping(report.get("report"), "report.yaml:report")),
        "runtime_policy": deepcopy(
            _mapping(report.get("runtime_policy"), "report.yaml:runtime_policy")
        ),
        "defaults": deepcopy(_mapping(report.get("defaults"), "report.yaml:defaults")),
        "sections": deepcopy(_mapping(report.get("sections"), "report.yaml:sections")),
        "catalogs": {
            "queries": deepcopy(_mapping(query_catalog.get("query_catalog"), "query_catalog")),
            "scripts": deepcopy(_mapping(script_catalog.get("script_catalog"), "script_catalog")),
            "metrics": deepcopy(_mapping(metric_catalog.get("metric_catalog"), "metric_catalog")),
            "python": {},
            "presentation": {"units": _default_units()},
        },
        "queries": deepcopy(queries),
        "scripts": deepcopy(scripts),
        "metrics": deepcopy(metrics),
        "python_sources": {},
        "sampler_providers": deepcopy(sampler_providers),
        "instructions": {
            item_id: {"path": provenance[f"instructions/{item_id}"][0]}
            for item_id in instructions
        },
        "field_reference": {},
    }
    pack = ContentPack(
        path=root,
        report=report,
        queries=queries,
        scripts=scripts,
        metrics=metrics,
        sampler_providers=sampler_providers,
        instructions=instructions,
        document=document,
        provenance=provenance,
        checksum=checksum,
    )
    validate_content(pack)
    return pack


def _mapping(value: Any, label: str) -> dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ContentValidationError(f"{label} must be a mapping")
    return value


def iter_report_items(content: ContentPack) -> Iterator[tuple[str, str, str, dict[str, Any]]]:
    yield from iter_report_items_from_report(content.report)


def iter_report_items_from_report(
    report: dict[str, Any],
) -> Iterator[tuple[str, str, str, dict[str, Any]]]:
    for section_id, section in _mapping(report.get("sections"), "report.sections").items():
        if not isinstance(section, dict):
            raise ContentValidationError(f"section {section_id!r} must be a mapping")
        for item_key, item in _mapping(section.get("items"), f"section {section_id}.items").items():
            if not isinstance(item, dict):
                raise ContentValidationError(f"item {section_id}.{item_key} must be a mapping")
            yield section_id, item_key, f"{section_id}.{item_key}", item


def validate_content(content: ContentPack) -> None:
    report_meta = _mapping(content.report.get("report"), "report.yaml:report")
    if report_meta.get("schema_version") != CONTENT_SCHEMA_VERSION:
        raise ContentValidationError(
            f"content schema must be {CONTENT_SCHEMA_VERSION}, got {report_meta.get('schema_version')!r}"
        )
    if not report_meta.get("id") or not report_meta.get("title"):
        raise ContentValidationError("report id and title are required")
    allowed_tags = set(report_meta.get("allowed_item_tags") or [])
    seen: set[str] = set()
    for section_id, _item_key, item_id, item in iter_report_items(content):
        if item_id in seen:
            raise ContentValidationError(f"duplicate report item {item_id}")
        seen.add(item_id)
        source_keys = [key for key in ("query", "script", "metric") if item.get(key)]
        if len(source_keys) != 1:
            raise ContentValidationError(f"{item_id} must reference exactly one source")
        source_kind = source_keys[0]
        source_id = str(item[source_kind])
        source_catalog = {
            "query": content.queries,
            "script": content.scripts,
            "metric": content.metrics,
        }[source_kind]
        if source_id not in source_catalog:
            raise ContentValidationError(f"{item_id} references missing {source_kind} {source_id!r}")
        tags = item.get("tags") or []
        if not isinstance(tags, list) or not tags:
            raise ContentValidationError(f"{item_id} must define at least one tag")
        unknown = [tag for tag in tags if tag not in allowed_tags]
        if unknown:
            raise ContentValidationError(f"{item_id} has unknown tags: {unknown!r}")
        state = item.get("state", "collapsed")
        if state not in {"expanded", "collapsed", "hidden"}:
            raise ContentValidationError(f"{item_id} has invalid state {state!r}")

    for query_id, query in content.queries.items():
        _validate_source_contract(query_id, query, expected_kind="table")
        requirements = _mapping(query.get("requires"), f"query {query_id}.requires")
        for table in requirements.get("tables") or []:
            if not _qualified_identifier(str(table), 2):
                raise ContentValidationError(f"query {query_id} has invalid required table {table!r}")
        for column in requirements.get("columns") or []:
            if not _qualified_identifier(str(column), 3):
                raise ContentValidationError(f"query {query_id} has invalid required column {column!r}")
        variants = query.get("variants") or []
        if not isinstance(variants, list) or not variants:
            raise ContentValidationError(f"query {query_id} must define variants")
        for variant in variants:
            if not isinstance(variant, dict) or not variant.get("id") or not variant.get("sql_file"):
                raise ContentValidationError(f"query {query_id} has invalid variant")
            scopes = set(variant.get("scopes") or ["node", "cluster"])
            if not scopes or not scopes <= {"node", "cluster"}:
                raise ContentValidationError(f"query {query_id} variant has invalid scopes")
            sql_path = _safe_path(content.path / "queries", str(variant["sql_file"]), query_id)
            if not sql_path.is_file():
                raise ContentValidationError(f"query {query_id} SQL file is missing: {sql_path}")
            sql = sql_path.read_text(encoding="utf-8")
            _validate_read_only_sql(sql, query_id)
            if "node" in scopes and "{{cluster}}" in sql:
                raise ContentValidationError(
                    f"query {query_id} node variant contains a cluster placeholder"
                )
            try:
                minimum = ClickHouseVersion.parse(str(variant.get("min_ch_version", "0")))
                maximum_value = variant.get("max_ch_version")
                maximum = (
                    ClickHouseVersion.parse(str(maximum_value))
                    if maximum_value is not None
                    else None
                )
            except ValueError as exc:
                raise ContentValidationError(f"query {query_id} has invalid version range") from exc
            if maximum is not None and maximum <= minimum:
                raise ContentValidationError(f"query {query_id} has an empty version range")
        _validate_variant_ranges(query_id, variants)

    for script_id, script in content.scripts.items():
        _validate_source_contract(script_id, script, expected_kind=None)
        file_name = script.get("file")
        if not file_name:
            raise ContentValidationError(f"script {script_id} has no file")
        script_path = _safe_path(content.path / "scripts", str(file_name), script_id)
        if not script_path.is_file():
            raise ContentValidationError(f"script {script_id} file is missing: {script_path}")
        library = script.get("library")
        if library:
            library_path = _safe_path(content.path / "scripts", str(library), script_id)
            if not library_path.is_file():
                raise ContentValidationError(
                    f"script {script_id} library is missing: {library_path}"
                )

    declared_outputs = {
        str(output_id)
        for provider in content.sampler_providers.values()
        for output_id in _mapping(provider.get("outputs"), "sampler outputs")
    }
    for provider_id, provider in content.sampler_providers.items():
        config = _mapping(provider.get("config"), f"sampler {provider_id}.config")
        for key, value in config.items():
            if str(key).endswith(("_script", "_library")):
                script_path = _safe_path(content.path / "scripts", str(value), provider_id)
                if not script_path.is_file():
                    raise ContentValidationError(
                        f"sampler {provider_id} script is missing: {script_path}"
                    )
    for metric_id, metric in content.metrics.items():
        _validate_source_contract(metric_id, metric, expected_kind="chart")
        sources = [key for key in ("source_query", "source_sampler") if metric.get(key)]
        if len(sources) != 1:
            raise ContentValidationError(
                f"metric {metric_id} must reference exactly one query or sampler"
            )
        if metric.get("source_query") not in {None, *content.queries}:
            raise ContentValidationError(
                f"metric {metric_id} references missing query {metric.get('source_query')!r}"
            )
        if metric.get("source_sampler") not in {None, *declared_outputs}:
            raise ContentValidationError(
                f"metric {metric_id} references missing sampler output {metric.get('source_sampler')!r}"
            )
        series = metric.get("series") or []
        if not isinstance(series, list) or not series:
            raise ContentValidationError(f"metric {metric_id} must define series")
        for entry in series:
            if not isinstance(entry, dict) or not entry.get("value_ref"):
                raise ContentValidationError(f"metric {metric_id} has invalid series")
            if entry.get("transform", "gauge") not in {"gauge", "rate", "delta"}:
                raise ContentValidationError(f"metric {metric_id} has invalid transform")


def _validate_source_contract(
    source_id: str,
    source: dict[str, Any],
    *,
    expected_kind: str | None,
) -> None:
    scope = source.get("collection_scope")
    if scope not in {"once", "every_snapshot"}:
        raise ContentValidationError(
            f"source {source_id} has invalid collection_scope {scope!r}"
        )
    if source.get("cost_class") not in {"low", "medium", "high"}:
        raise ContentValidationError(f"source {source_id} has invalid cost_class")
    if not source.get("privilege_profile"):
        raise ContentValidationError(f"source {source_id} has no privilege_profile")
    result_contract = _mapping(
        source.get("result_contract"),
        f"source {source_id}.result_contract",
    )
    if expected_kind is not None and result_contract.get("kind") != expected_kind:
        raise ContentValidationError(
            f"source {source_id} result contract must be {expected_kind}"
        )
    if result_contract.get("unit_policy") not in {
        "raw",
        "raw_then_renderer_scaled",
    }:
        raise ContentValidationError(f"source {source_id} has invalid unit policy")


def _validate_variant_ranges(query_id: str, variants: list[dict[str, Any]]) -> None:
    for scope in ("node", "cluster"):
        ranged = []
        for variant in variants:
            if scope not in set(variant.get("scopes") or ["node", "cluster"]):
                continue
            minimum = ClickHouseVersion.parse(str(variant.get("min_ch_version", "0")))
            maximum_value = variant.get("max_ch_version")
            maximum = (
                ClickHouseVersion.parse(str(maximum_value))
                if maximum_value is not None
                else None
            )
            ranged.append((minimum, maximum, str(variant["id"])))
        ranged.sort(key=lambda entry: entry[0])
        for left, right in zip(ranged, ranged[1:]):
            if left[1] is None or right[0] < left[1]:
                raise ContentValidationError(
                    f"query {query_id} has overlapping {scope} variants "
                    f"{left[2]!r} and {right[2]!r}"
                )


def _validate_read_only_sql(sql: str, query_id: str) -> None:
    cleaned = "\n".join(
        line for line in sql.splitlines() if not line.lstrip().startswith("--")
    ).strip()
    if cleaned.endswith(";"):
        cleaned = cleaned[:-1].rstrip()
    if ";" in cleaned:
        raise ContentValidationError(f"query {query_id} contains multiple statements")
    first = cleaned.split(None, 1)[0].upper() if cleaned else ""
    if first not in {"SELECT", "WITH", "SHOW", "EXPLAIN"}:
        raise ContentValidationError(f"query {query_id} is not an allowed read-only statement")
    upper = " " + cleaned.upper() + " "
    forbidden = (" INTO OUTFILE ", " INSERT ", " ALTER ", " DROP ", " CREATE ", " TRUNCATE ")
    if any(token in upper for token in forbidden):
        raise ContentValidationError(f"query {query_id} contains a forbidden SQL construct")


def _qualified_identifier(value: str, parts: int) -> bool:
    tokens = value.split(".")
    return len(tokens) == parts and all(
        token and token.replace("_", "a").isalnum() and not token[0].isdigit()
        for token in tokens
    )


def _default_units() -> dict[str, dict[str, Any]]:
    return {
        "none": {"kind": "none"},
        "count": {"kind": "decimal", "adaptive": True},
        "bytes": {"kind": "bytes", "adaptive": True},
        "bytes/s": {"kind": "bytes_rate", "adaptive": True},
        "%": {"kind": "percent"},
        "ms": {"kind": "duration_ms"},
        "s": {"kind": "duration_s"},
        "queries/s": {"kind": "decimal"},
        "rows/s": {"kind": "decimal"},
    }
