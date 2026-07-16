from __future__ import annotations

from pathlib import Path
import asyncio
import hashlib
import shutil

import pytest
import yaml

from ch_diag.content_loader import default_content_path, load_content
from ch_diag.clickhouse import ConnectionConfig
from ch_diag.collector import collect_snapshots
from ch_diag.errors import ContentIntegrityError
from ch_diag.planner import available_item_ids, build_plan
from ch_diag.versioning import ClickHouseVersion
from tools.sync_pg_diag_os_content import metric_digest


def test_vendor_content_loads_and_covers_legacy_inventory() -> None:
    content = load_content()
    ids = available_item_ids(content)
    legacy = [query for query in content.queries if query.startswith("legacy.")]
    assert len(legacy) == 55
    assert len(ids) >= 100
    assert "snapshot_charts_clickhouse.query_rate" in ids
    assert "dba_troubleshooting.column_compression" in ids


def test_integrity_is_verified_before_yaml_is_trusted(tmp_path: Path) -> None:
    destination = tmp_path / "content"
    shutil.copytree(default_content_path(), destination)
    report = destination / "report.yaml"
    report.write_text(report.read_text(encoding="utf-8") + "\n# tampered\n", encoding="utf-8")
    with pytest.raises(ContentIntegrityError, match="trusted distribution"):
        load_content(destination)


def test_node_plan_has_explicit_legacy_variants_and_keeps_cluster_comparisons_out() -> None:
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
    assert "legacy_node/" in str(by_id["query_workload.queries_top_long"].sql_file)


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
