"""Build execution plans from schema-version-5 ch_diag content."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any, Iterable

from .content_loader import ContentPack, iter_report_items
from .errors import UnsupportedClickHouseVersion
from .runtime_config import REMOTE_DB_ONLY_COLLECTION_MODE, SNAPSHOTS_MODE
from .versioning import ClickHouseVersion, resolve_lts_branch, select_variant


@dataclass(frozen=True)
class PlannedItem:
    item_id: str
    section_id: str
    item_key: str
    title: str
    source_kind: str
    source_id: str
    status: str
    state: str
    reason: str | None = None
    variant_id: str | None = None
    sql_file: str | None = None
    script_file: str | None = None
    targets: tuple[str, ...] = ()
    source_metadata: dict[str, Any] = field(default_factory=dict)
    fallback_on: tuple[str, ...] = ()
    fallback_item: "PlannedItem | None" = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "item_id": self.item_id,
            "section_id": self.section_id,
            "item_key": self.item_key,
            "title": self.title,
            "source_kind": self.source_kind,
            "source_id": self.source_id,
            "status": self.status,
            "state": self.state,
            "reason": self.reason,
            "variant_id": self.variant_id,
            "sql_file": self.sql_file,
            "script_file": self.script_file,
            "targets": list(self.targets),
            "source_metadata": self.source_metadata,
            "fallback_on": list(self.fallback_on),
            "fallback_item": self.fallback_item.to_dict() if self.fallback_item else None,
        }


@dataclass(frozen=True)
class ExecutionPlan:
    mode: str
    collection_mode: str
    target_scope: str
    server_version: ClickHouseVersion | None
    compatibility_lts_version: str | None
    sections: list[dict[str, Any]]
    items: list[PlannedItem]


@dataclass(frozen=True)
class CollectionRequirements:
    host_item_ids: tuple[str, ...]
    database_item_ids: tuple[str, ...]

    @property
    def requires_host(self) -> bool:
        return bool(self.host_item_ids)

    @property
    def requires_database(self) -> bool:
        return bool(self.database_item_ids)

    @property
    def targets(self) -> tuple[str, ...]:
        return tuple(
            target
            for target, required in (
                ("host", self.requires_host),
                ("database", self.requires_database),
            )
            if required
        )

    def requires_ssh(self, collection_mode: str) -> bool:
        return collection_mode == "remote" and bool(self.targets)


def available_item_ids(content: ContentPack) -> list[str]:
    return [item_id for _section, _key, item_id, _item in iter_report_items(content)]


def available_tags(content: ContentPack) -> list[str]:
    return sorted(
        {
            str(tag)
            for _section, _key, _item_id, item in iter_report_items(content)
            for tag in (item.get("tags") or [])
        },
        key=str.casefold,
    )


def _normalized_filter(value: str | Iterable[str] | None) -> tuple[str, ...] | None:
    if value is None:
        return None
    values = [value] if isinstance(value, str) else list(value)
    result: list[str] = []
    for raw in values:
        for part in str(raw).split(","):
            normalized = part.strip()
            if normalized and normalized not in result:
                result.append(normalized)
    return tuple(result)


def _selected_filters(
    content: ContentPack,
    item_ids: str | Iterable[str] | None,
    tags: str | Iterable[str] | None,
) -> tuple[tuple[str, ...] | None, set[str] | None]:
    requested_items = _normalized_filter(item_ids)
    requested_tags = _normalized_filter(tags)
    if requested_items is not None and requested_tags is not None:
        raise ValueError("--item-id and --tags cannot be used together")
    known_items = set(available_item_ids(content))
    if requested_items is not None:
        unknown = sorted(set(requested_items) - known_items)
        if unknown:
            raise ValueError("Unknown report item(s): " + ", ".join(unknown))
    canonical_tags = {tag.casefold(): tag for tag in available_tags(content)}
    if requested_tags is None:
        return requested_items, None
    unknown_tags = [tag for tag in requested_tags if tag.casefold() not in canonical_tags]
    if unknown_tags:
        raise ValueError("Unknown report tag(s): " + ", ".join(unknown_tags))
    return requested_items, {canonical_tags[tag.casefold()] for tag in requested_tags}


def collection_requirements(
    content: ContentPack,
    *,
    mode: str,
    collection_mode: str,
    target_scope: str,
    item_ids: str | Iterable[str] | None = None,
    tags: str | Iterable[str] | None = None,
) -> CollectionRequirements:
    """Resolve host/database transports before opening either connection."""

    requested_items, requested_tags = _selected_filters(content, item_ids, tags)
    host_items: list[str] = []
    database_items: list[str] = []
    for _section_id, _item_key, item_id, item in iter_report_items(content):
        if requested_items is not None and item_id not in requested_items:
            continue
        item_tags = set(str(tag) for tag in item.get("tags") or [])
        if requested_tags is not None and not requested_tags.intersection(item_tags):
            continue
        source_kind = next(key for key in ("query", "script", "metric") if item.get(key))
        source_id = str(item[source_kind])
        targets = _source_targets(content, source_kind, source_id)
        if source_kind == "metric" and mode != SNAPSHOTS_MODE:
            continue
        if collection_mode == REMOTE_DB_ONLY_COLLECTION_MODE and targets == ("host",):
            continue
        if "host" in targets:
            host_items.append(item_id)
        if "database" in targets:
            database_items.append(item_id)
    if target_scope == "cluster" and not database_items:
        database_items.append("<cluster-target-resolution>")
    return CollectionRequirements(tuple(host_items), tuple(database_items))


def _source_targets(
    content: ContentPack,
    source_kind: str,
    source_id: str,
) -> tuple[str, ...]:
    if source_kind == "query":
        return ("database",)
    if source_kind == "script":
        return ("host",)
    metric = content.metrics[source_id]
    return ("database",) if metric.get("source_query") else ("host",)


def build_plan(
    content: ContentPack,
    server_version: ClickHouseVersion | None,
    *,
    mode: str,
    collection_mode: str,
    target_scope: str,
    item_ids: str | Iterable[str] | None = None,
    tags: str | Iterable[str] | None = None,
) -> ExecutionPlan:
    requested_items, requested_tag_set = _selected_filters(content, item_ids, tags)
    requirements = collection_requirements(
        content,
        mode=mode,
        collection_mode=collection_mode,
        target_scope=target_scope,
        item_ids=requested_items,
        tags=requested_tag_set,
    )
    if requirements.requires_database and server_version is None:
        raise ValueError("ClickHouse server version is required by selected database items")
    compatibility_lts_version = (
        resolve_lts_branch(server_version, content.supported_lts_versions)
        if server_version is not None
        else None
    )
    if server_version is not None and compatibility_lts_version is None:
        supported = ", ".join(content.supported_lts_versions)
        raise UnsupportedClickHouseVersion(
            f"ClickHouse {server_version} predates the earliest supported LTS branch; "
            f"LTS compatibility anchors: {supported}"
        )
    items: list[PlannedItem] = []
    section_items: dict[str, list[str]] = {}
    for section_id, item_key, item_id, item in iter_report_items(content):
        if requested_items is not None and item_id not in requested_items:
            continue
        item_tags = list(item.get("tags") or [])
        if requested_tag_set is not None and not requested_tag_set.intersection(item_tags):
            continue
        source_kind = next(key for key in ("query", "script", "metric") if item.get(key))
        source_id = str(item[source_kind])
        targets = _source_targets(content, source_kind, source_id)
        title = str(
            item.get("title")
            or {"query": content.queries, "script": content.scripts, "metric": content.metrics}[
                source_kind
            ][source_id].get("title")
            or item_key
        )
        state = str(item.get("state") or "collapsed")
        metadata: dict[str, Any] = {
            "tags": item_tags,
            "execution_scope": target_scope,
            "render": dict(item.get("render") or {}),
        }
        instruction = content.instructions.get(item_id)
        if instruction:
            metadata["instructions"] = {"text": instruction}
        status = "planned"
        reason = None
        variant_id = sql_file = script_file = None
        if source_kind == "query":
            assert server_version is not None
            query = content.queries[source_id]
            variant = select_variant(
                list(query.get("variants") or []),
                server_version,
                target_scope,
                content.supported_lts_versions,
            )
            if variant is None:
                status = "skipped"
                reason = f"no {target_scope} SQL variant for ClickHouse {server_version}"
            else:
                variant_id = str(variant["id"])
                sql_file = str(variant["sql_file"])
                metadata.update(
                    {
                        "variant_id": variant_id,
                        "sql_file": sql_file,
                        "display": dict(query.get("display") or {}),
                        "sensitivity": query.get("sensitivity", "normal"),
                    }
                )
        elif source_kind == "script":
            script = content.scripts[source_id]
            script_file = str(script["file"])
            metadata.update(
                {
                    "script_file": script_file,
                    "source_language": "bash",
                    "display": dict(script.get("display") or {}),
                }
            )
            if collection_mode == REMOTE_DB_ONLY_COLLECTION_MODE:
                status = "skipped"
                reason = "host collection is unavailable in remote-db-only mode"
        elif source_kind == "metric":
            metric = content.metrics[source_id]
            if (metric.get("result_contract") or {}).get("kind") == "table":
                metadata["display"] = dict(metric.get("display") or {})
            else:
                metadata["chart"] = dict(metric.get("chart") or {})
            if mode != SNAPSHOTS_MODE:
                status = "skipped"
                reason = "requires snapshots mode"
            elif collection_mode == REMOTE_DB_ONLY_COLLECTION_MODE and metric.get("source_sampler"):
                status = "skipped"
                reason = "host sampling is unavailable in remote-db-only mode"

        planned = PlannedItem(
            item_id=item_id,
            section_id=section_id,
            item_key=item_key,
            title=title,
            source_kind=source_kind,
            source_id=source_id,
            status=status,
            state=state,
            reason=reason,
            variant_id=variant_id,
            sql_file=sql_file,
            script_file=script_file,
            source_metadata=metadata,
            targets=targets,
        )
        planned = _attach_fallback(
            content,
            planned,
            item,
            server_version,
            target_scope,
            collection_mode,
        )
        items.append(planned)
        section_items.setdefault(section_id, []).append(item_id)

    sections: list[dict[str, Any]] = []
    for section_id, section in (content.report.get("sections") or {}).items():
        if not section_items.get(section_id):
            continue
        sections.append(
            {
                "section_id": section_id,
                "title": section.get("title") or section_id,
                "description": section.get("description"),
                "state": section.get("state", "expanded"),
                "items": section_items[section_id],
            }
        )
    if requested_items is not None or requested_tag_set is not None:
        items = [
            replace(item, state="expanded") if item.state != "hidden" else item
            for item in items
        ]
        sections = [
            {
                **section,
                "state": "expanded" if section.get("state") != "hidden" else "hidden",
            }
            for section in sections
        ]
    return ExecutionPlan(
        mode=mode,
        collection_mode=collection_mode,
        target_scope=target_scope,
        server_version=server_version,
        compatibility_lts_version=compatibility_lts_version,
        sections=sections,
        items=items,
    )


def _attach_fallback(
    content: ContentPack,
    planned: PlannedItem,
    item: dict[str, Any],
    server_version: ClickHouseVersion | None,
    target_scope: str,
    collection_mode: str,
) -> PlannedItem:
    fallback_item_id = item.get("fallback_item")
    if not fallback_item_id:
        return planned
    definition = (content.report.get("fallback_items") or {})[fallback_item_id]
    source_kind = next(key for key in ("query", "script") if definition.get(key))
    source_id = str(definition[source_kind])
    title = str(
        definition.get("title")
        or (content.queries if source_kind == "query" else content.scripts)[source_id].get(
            "title"
        )
        or fallback_item_id
    )
    status = "planned"
    reason = None
    variant_id = sql_file = script_file = None
    metadata: dict[str, Any] = {
        "execution_scope": target_scope,
        "render": dict(definition.get("render") or {}),
    }
    instruction = content.instructions.get(str(fallback_item_id))
    if instruction:
        metadata["instructions"] = {"text": instruction}
    if source_kind == "query":
        if server_version is None:
            raise ValueError("ClickHouse server version is required by query fallback items")
        manifest = content.queries[source_id]
        variant = select_variant(
            list(manifest.get("variants") or []),
            server_version,
            target_scope,
            content.supported_lts_versions,
        )
        if variant is None:
            status = "skipped"
            reason = f"no {target_scope} SQL variant for ClickHouse {server_version}"
        else:
            variant_id = str(variant["id"])
            sql_file = str(variant["sql_file"])
            metadata.update(
                {
                    "variant_id": variant_id,
                    "sql_file": sql_file,
                    "display": dict(manifest.get("display") or {}),
                    "sensitivity": manifest.get("sensitivity", "normal"),
                }
            )
    else:
        manifest = content.scripts[source_id]
        script_file = str(manifest["file"])
        metadata.update(
            {
                "script_file": script_file,
                "source_language": "bash",
                "display": dict(manifest.get("display") or {}),
            }
        )
        if collection_mode == REMOTE_DB_ONLY_COLLECTION_MODE:
            status = "skipped"
            reason = "host collection is unavailable in remote-db-only mode"
    fallback = PlannedItem(
        item_id=str(fallback_item_id),
        section_id=planned.section_id,
        item_key=planned.item_key,
        title=title,
        source_kind=source_kind,
        source_id=source_id,
        status=status,
        state=planned.state,
        reason=reason,
        variant_id=variant_id,
        sql_file=sql_file,
        script_file=script_file,
        targets=_source_targets(content, source_kind, source_id),
        source_metadata=metadata,
    )
    fallback_on = tuple(str(value) for value in item.get("fallback_on") or ())
    return replace(
        planned,
        source_metadata={
            **planned.source_metadata,
            "fallback_policy": {
                "fallback_item_id": fallback_item_id,
                "on": list(fallback_on),
            },
        },
        fallback_on=fallback_on,
        fallback_item=fallback,
    )
