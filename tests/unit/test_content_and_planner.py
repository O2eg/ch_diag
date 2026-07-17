from __future__ import annotations

from pathlib import Path
import asyncio
import hashlib
import shutil

import pytest
import yaml

from ch_diag.content_loader import (
    default_content_path,
    iter_report_items,
    load_content,
    validate_content,
)
from ch_diag.clickhouse import ConnectionConfig
from ch_diag.collector import collect_snapshots
from ch_diag.errors import ContentIntegrityError
from ch_diag.errors import ContentValidationError
from ch_diag.errors import UnsupportedClickHouseVersion
from ch_diag.planner import available_item_ids, build_plan
from ch_diag.versioning import ClickHouseVersion
from tools.sync_pg_diag_os_content import metric_digest


def test_vendor_content_loads_and_covers_diagnostic_inventory() -> None:
    content = load_content()
    ids = available_item_ids(content)
    diagnostics = [query for query in content.queries if query.startswith("diagnostics.")]
    assert len(diagnostics) == 55
    assert len(ids) >= 100
    assert "snapshot_charts_clickhouse.query_rate" in ids
    assert "dba_troubleshooting.column_compression" in ids
    assert content.supported_lts_versions == (
        "20.3",
        "20.8",
        "21.3",
        "21.8",
        "22.3",
        "22.8",
        "23.3",
        "23.8",
        "24.3",
        "24.8",
        "25.3",
        "25.8",
        "26.3",
    )


def test_every_report_item_has_structured_dba_instruction() -> None:
    content = load_content()
    item_ids = []
    required_sections = (
        "## What this item shows",
        "## What to watch",
        "## Common fault causes",
        "## Automatic evaluation",
        "## Checklist",
    )
    for _section_id, _item_key, item_id, _item in iter_report_items(content):
        item_ids.append(item_id)
        instruction = content.instructions[item_id]
        assert instruction.startswith("# "), item_id
        assert all(instruction.count(section) == 1 for section in required_sections), item_id
        assert [instruction.index(section) for section in required_sections] == sorted(
            instruction.index(section) for section in required_sections
        ), item_id
    assert set(content.instructions) == set(item_ids)


def test_content_rejects_an_incomplete_instruction() -> None:
    content = load_content()
    content.instructions["overview.server"] = "# Server\n\nNo investigation guidance.\n"

    with pytest.raises(ContentValidationError, match="What this item shows"):
        validate_content(content)


def test_every_query_scope_covers_every_supported_lts_branch() -> None:
    content = load_content()
    for query_id, query in content.queries.items():
        variants = list(query["variants"])
        scopes = {
            scope
            for variant in variants
            for scope in variant.get("scopes", ["node", "cluster"])
        }
        for scope in scopes:
            for branch in content.supported_lts_versions:
                matches = [
                    variant
                    for variant in variants
                    if scope in variant.get("scopes", ["node", "cluster"])
                    and branch in variant["lts_versions"]
                ]
                assert len(matches) == 1, (query_id, scope, branch)


def test_every_sql_backed_metric_owns_a_dedicated_query() -> None:
    content = load_content()
    consumers: dict[str, list[str]] = {}
    for metric_id, metric in content.metrics.items():
        if metric.get("source_query"):
            consumers.setdefault(str(metric["source_query"]), []).append(metric_id)

    assert len(consumers) == 24
    assert all(len(metric_ids) == 1 for metric_ids in consumers.values())

    sql_file_queries: dict[str, set[str]] = {}
    for query_id, query in content.queries.items():
        for variant in query["variants"]:
            sql_file_queries.setdefault(str(variant["sql_file"]), set()).add(query_id)
    assert all(len(query_ids) == 1 for query_ids in sql_file_queries.values())


def test_content_rejects_a_query_shared_by_multiple_metric_items() -> None:
    content = load_content()
    content.metrics["clickhouse.keeper_events"]["source_query"] = "metrics.query_rate"

    with pytest.raises(ContentValidationError, match="must own a dedicated query"):
        validate_content(content)


def test_non_lts_clickhouse_branch_uses_nearest_preceding_lts() -> None:
    content = load_content()
    non_lts = build_plan(
        content,
        ClickHouseVersion.parse("22.9.7.1"),
        mode="one-shot",
        collection_mode="remote-db-only",
        target_scope="node",
    )
    lts = build_plan(
        content,
        ClickHouseVersion.parse("22.8.21.38"),
        mode="one-shot",
        collection_mode="remote-db-only",
        target_scope="node",
    )
    assert non_lts.compatibility_lts_version == "22.8"
    assert {
        item.item_id: item.variant_id for item in non_lts.items
    } == {
        item.item_id: item.variant_id for item in lts.items
    }


def test_clickhouse_older_than_first_lts_is_rejected() -> None:
    content = load_content()
    with pytest.raises(UnsupportedClickHouseVersion, match="earliest supported LTS"):
        build_plan(
            content,
            ClickHouseVersion.parse("20.2"),
            mode="one-shot",
            collection_mode="remote-db-only",
            target_scope="node",
        )


def test_integrity_is_verified_before_yaml_is_trusted(tmp_path: Path) -> None:
    destination = tmp_path / "content"
    shutil.copytree(default_content_path(), destination)
    report = destination / "report.yaml"
    report.write_text(report.read_text(encoding="utf-8") + "\n# tampered\n", encoding="utf-8")
    with pytest.raises(ContentIntegrityError, match="trusted distribution"):
        load_content(destination)


def test_node_plan_has_explicit_diagnostic_variants_and_keeps_cluster_comparisons_out() -> None:
    content = load_content()
    plan = build_plan(
        content,
        ClickHouseVersion.parse("25.8.28.1"),
        mode="one-shot",
        collection_mode="remote-db-only",
        target_scope="node",
    )
    by_id = {item.item_id: item for item in plan.items}
    assert by_id["clickhouse_system.system_common"].status == "planned"
    assert by_id["databases_objects.db_asymmetric_tbls"].status == "skipped"
    assert "node/" in str(by_id["query_workload.queries_top_long"].sql_file)


def test_filters_are_arrays_and_mutually_exclusive() -> None:
    content = load_content()
    plan = build_plan(
        content,
        ClickHouseVersion.parse("25.8"),
        mode="one-shot",
        collection_mode="local",
        target_scope="node",
        item_ids="overview.server,overview.clusters",
    )
    assert [item.item_id for item in plan.items] == ["overview.server", "overview.clusters"]
    with pytest.raises(ValueError, match="cannot be used together"):
        build_plan(
            content,
            ClickHouseVersion.parse("25.8"),
            mode="one-shot",
            collection_mode="local",
            target_scope="node",
            item_ids=["overview.server"],
            tags=["Cluster"],
        )


def test_vendored_os_scripts_match_local_upstream_lock() -> None:
    root = default_content_path()
    lock = yaml.safe_load((root / "UPSTREAM_OS_CONTENT.lock.yaml").read_text(encoding="utf-8"))
    assert lock["upstream"]["tag"] == "v0.9.0"
    assert len(lock["files"]) == 27
    for entry in lock["files"]:
        value = hashlib.sha256((root / entry["target"]).read_bytes()).hexdigest()
        assert value == entry["sha256"] == entry["donor_sha256"]
    metrics = yaml.safe_load((root / "metrics.yaml").read_text(encoding="utf-8"))["metrics"]
    assert len(lock["metric_contracts"]) == 12
    for entry in lock["metric_contracts"]:
        value = metric_digest(metrics[entry["id"]])
        assert value == entry["sha256"] == entry["donor_sha256"]


def test_snapshot_count_budget_fails_before_connecting() -> None:
    content = load_content()
    with pytest.raises(ValueError, match="above limit 360"):
        asyncio.run(
            collect_snapshots(
                content,
                ConnectionConfig(),
                out_dir="unused",
                collection_mode="remote-db-only",
                target_scope="node",
                duration_seconds=100,
                interval_seconds=0.2,
            )
        )
