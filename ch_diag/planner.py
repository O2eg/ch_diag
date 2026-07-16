"""Build execution plans from schema-version-5 ch_diag content."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable

from .content_loader import ContentPack, iter_report_items
from .runtime_config import REMOTE_DB_ONLY_COLLECTION_MODE, SNAPSHOTS_MODE
from .versioning import ClickHouseVersion, select_variant


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
    source_metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ExecutionPlan:
    mode: str
    collection_mode: str
    target_scope: str
    server_version: ClickHouseVersion
    sections: list[dict[str, Any]]
    items: list[PlannedItem]


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


def build_plan(
    content: ContentPack,
    server_version: ClickHouseVersion,
    *,
    mode: str,
    collection_mode: str,
    target_scope: str,
    item_ids: str | Iterable[str] | None = None,
    tags: str | Iterable[str] | None = None,
) -> ExecutionPlan:
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
    if requested_tags is not None:
        unknown_tags = [tag for tag in requested_tags if tag.casefold() not in canonical_tags]
        if unknown_tags:
            raise ValueError("Unknown report tag(s): " + ", ".join(unknown_tags))
        requested_tag_set = {canonical_tags[tag.casefold()] for tag in requested_tags}
    else:
        requested_tag_set = None

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
            query = content.queries[source_id]
            variant = select_variant(list(query.get("variants") or []), server_version, target_scope)
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
    return ExecutionPlan(
        mode=mode,
        collection_mode=collection_mode,
        target_scope=target_scope,
        server_version=server_version,
        sections=sections,
        items=items,
    )
