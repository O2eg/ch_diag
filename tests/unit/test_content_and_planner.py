from __future__ import annotations

from pathlib import Path
import asyncio
import hashlib
import shutil

import pytest
import yaml

import ch_diag.content_loader as content_loader_module
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
from ch_diag.planner import available_item_ids, build_plan, collection_requirements
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
    for item_id in content.report["fallback_items"]:
        instruction = content.instructions[item_id]
        assert instruction.startswith("# "), item_id
        assert all(instruction.count(section) == 1 for section in required_sections), item_id
    assert set(content.instructions) == set(item_ids) | set(content.report["fallback_items"])


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


def test_content_rejects_non_positive_process_thread_limit() -> None:
    content = load_content()
    content.sampler_providers["linux_os"]["config"]["max_process_threads"] = 0

    with pytest.raises(ContentValidationError, match="max_process_threads"):
        validate_content(content)


def test_content_requires_positive_query_read_limits() -> None:
    content = load_content()
    content.report["runtime_policy"]["max_query_rows_read"] = 0

    with pytest.raises(ContentValidationError, match="max_query_rows_read"):
        validate_content(content)


def test_high_cost_report_queries_declare_truthful_final_row_limits() -> None:
    content = load_content()
    high_cost_queries = {
        str(item["query"])
        for _section, _key, _item_id, item in iter_report_items(content)
        if item.get("query")
        and content.queries[str(item["query"])].get("cost_class") == "high"
    }

    assert len(high_cost_queries) == 17
    assert all(
        isinstance(
            (content.queries[query_id].get("result_contract") or {}).get("row_limit"),
            int,
        )
        for query_id in high_cost_queries
    )


def test_declared_query_row_limit_must_match_every_variant() -> None:
    content = load_content()
    content.queries["overview.server"]["result_contract"]["row_limit"] = 1

    with pytest.raises(ContentValidationError, match="no matching final LIMIT"):
        validate_content(content)


def test_content_requires_boolean_fail_fast_policy() -> None:
    content = load_content()
    content.report["runtime_policy"]["fail_fast"] = "false"

    with pytest.raises(ContentValidationError, match="fail_fast"):
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


def test_cached_content_loads_verify_integrity_and_return_isolated_copies(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    destination = tmp_path / "content"
    shutil.copytree(default_content_path(), destination)
    content_loader_module._load_content_revision.cache_clear()
    calls = {"verify": 0, "yaml": 0}
    original_verify = content_loader_module.verify_content_integrity
    original_load_yaml = content_loader_module._load_yaml

    def counted_verify(path: str | Path) -> str:
        calls["verify"] += 1
        return original_verify(path)

    def counted_load_yaml(path: Path) -> dict[str, object]:
        calls["yaml"] += 1
        return original_load_yaml(path)

    monkeypatch.setattr(content_loader_module, "verify_content_integrity", counted_verify)
    monkeypatch.setattr(content_loader_module, "_load_yaml", counted_load_yaml)

    first = load_content(destination)
    first.report["mutated_by_caller"] = True
    first.queries["overview.server"]["mutated_by_caller"] = True
    second = load_content(destination)

    assert calls == {"verify": 2, "yaml": 4}
    assert "mutated_by_caller" not in second.report
    assert "mutated_by_caller" not in second.queries["overview.server"]


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


def test_filtered_host_only_plan_needs_no_clickhouse_version_and_expands_selection() -> None:
    content = load_content()
    requirements = collection_requirements(
        content,
        mode="one-shot",
        collection_mode="local",
        target_scope="node",
        item_ids=["operating_system.kernel_version"],
    )
    assert requirements.requires_database is False
    assert requirements.requires_host is True

    plan = build_plan(
        content,
        None,
        mode="one-shot",
        collection_mode="local",
        target_scope="node",
        item_ids=["operating_system.kernel_version"],
    )
    assert plan.server_version is None
    assert plan.compatibility_lts_version is None
    assert plan.items[0].targets == ("host",)
    assert plan.items[0].state == "expanded"
    assert plan.sections[0]["state"] == "expanded"


def test_target_requirements_distinguish_remote_host_database_and_db_only_modes() -> None:
    content = load_content()
    host = collection_requirements(
        content,
        mode="one-shot",
        collection_mode="remote",
        target_scope="node",
        item_ids=["operating_system.kernel_version"],
    )
    assert host.targets == ("host",)
    assert host.requires_ssh("remote") is True

    database = collection_requirements(
        content,
        mode="one-shot",
        collection_mode="remote",
        target_scope="node",
        item_ids=["overview.server"],
    )
    assert database.targets == ("database",)
    assert database.requires_ssh("remote") is True

    omitted_host = collection_requirements(
        content,
        mode="one-shot",
        collection_mode="remote-db-only",
        target_scope="node",
        item_ids=["operating_system.kernel_version"],
    )
    assert omitted_host.targets == ()


def test_fallback_manifest_is_validated_and_attached_to_parent_plan() -> None:
    content = load_content()
    content.report["fallback_items"].update(
        {
            "fallback.overview.server": {
                "title": "Fallback server query",
                "query": "overview.clusters",
            }
        }
    )
    content.report["sections"]["overview"]["items"]["server"].update(
        {
            "fallback_item": "fallback.overview.server",
            "fallback_on": ["query_timeout"],
        }
    )
    content.instructions["fallback.overview.server"] = content.instructions[
        "overview.clusters"
    ]
    validate_content(content)

    plan = build_plan(
        content,
        ClickHouseVersion.parse("25.8"),
        mode="one-shot",
        collection_mode="remote-db-only",
        target_scope="node",
        item_ids=["overview.server"],
    )
    item = plan.items[0]
    assert item.fallback_on == ("query_timeout",)
    assert item.fallback_item is not None
    assert item.fallback_item.item_id == "fallback.overview.server"


def test_bundled_high_cost_items_have_clickhouse_specific_fallbacks() -> None:
    content = load_content()
    fallback_items = content.report["fallback_items"]
    assert len(fallback_items) == 7

    parent_ids = [
        item_id
        for _section, _key, item_id, item in iter_report_items(content)
        if item.get("fallback_item")
    ]
    plans = [
        build_plan(
            content,
            ClickHouseVersion.parse("25.8"),
            mode="one-shot",
            collection_mode="remote-db-only",
            target_scope=scope,
            item_ids=parent_ids,
        )
        for scope in ("node", "cluster")
    ]
    assert all(
        item.status == "planned"
        and item.fallback_item is not None
        and item.fallback_item.status == "planned"
        for plan in plans
        for item in plan.items
    )

    by_id = {item.item_id: item for item in plans[0].items}
    profile = by_id["query_workload.queries_top_long_profile_events_agg"]
    storage = by_id["dba_troubleshooting.storage_breakdown"]
    assert profile.fallback_item is not None
    assert profile.fallback_item.source_id == "diagnostics.queries.queries_top_long_agg"
    assert "unsupported_capability" in profile.fallback_on
    assert storage.fallback_item is not None
    assert storage.fallback_item.source_id == "diagnostics.db.db_parts_stat"


def test_fallback_requires_known_item_and_normalized_trigger() -> None:
    content = load_content()
    item = content.report["sections"]["overview"]["items"]["server"]
    item["fallback_item"] = "missing"
    item["fallback_on"] = ["anything"]
    with pytest.raises(ContentValidationError, match="fallback"):
        validate_content(content)


def test_query_fallback_must_cover_every_primary_scope() -> None:
    content = load_content()
    content.report["fallback_items"]["fallback.overview.server"] = {
        "title": "Cluster-only fallback",
        "query": "diagnostics.queries.queries_by_hosts_common",
    }
    content.report["sections"]["overview"]["items"]["server"].update(
        {
            "fallback_item": "fallback.overview.server",
            "fallback_on": ["query_timeout"],
        }
    )
    content.instructions["fallback.overview.server"] = content.instructions[
        "overview.clusters"
    ]

    with pytest.raises(ContentValidationError, match="misses target scopes.*node"):
        validate_content(content)


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
