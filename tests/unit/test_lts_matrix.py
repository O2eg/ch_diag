from __future__ import annotations

from pathlib import Path

import yaml

from tools.normalize_sql_outputs import normalize_sql
from ch_diag.content_loader import load_content
from tools.run_lts_clickhouse_matrix import LTS_IMAGES, compatible_architecture


def test_lts_matrix_is_complete_and_pinned() -> None:
    assert tuple(LTS_IMAGES) == load_content().supported_lts_versions
    assert len({item.host_port for item in LTS_IMAGES.values()}) == len(
        LTS_IMAGES
    )
    assert len({item.container_name for item in LTS_IMAGES.values()}) == len(
        LTS_IMAGES
    )
    for item in LTS_IMAGES.values():
        assert item.version.startswith(item.branch + ".")
        assert item.digest.startswith("sha256:")
        assert len(item.digest) == len("sha256:") + 64
        assert "@sha256:" in item.reference


def test_ci_runs_only_the_catalog_lts_branches() -> None:
    repo = Path(__file__).resolve().parents[2]
    workflow = yaml.safe_load(
        (repo / ".github" / "workflows" / "tests.yml").read_text(encoding="utf-8")
    )
    jobs = workflow["jobs"]
    assert "clickhouse-legacy" not in jobs
    assert tuple(
        jobs["clickhouse-lts"]["strategy"]["matrix"]["branch"]
    ) == tuple(LTS_IMAGES)


def test_lts_architecture_gate() -> None:
    assert compatible_architecture("x86_64")
    assert compatible_architecture("AMD64")
    assert not compatible_architecture("aarch64")
    assert not compatible_architecture("arm64")


def test_supported_diagnostic_sql_is_self_contained_in_the_content_pack() -> None:
    repo = Path(__file__).resolve().parents[2]
    assert not (repo / "sql").exists()
    assert not (repo / "template").exists()

    content = repo / "ch_diag" / "content"
    queries = yaml.safe_load((content / "queries.yaml").read_text(encoding="utf-8"))[
        "queries"
    ]
    diagnostics = {
        query_id: manifest
        for query_id, manifest in queries.items()
        if manifest.get("source_item_id")
    }
    assert len(diagnostics) == 55
    for manifest in diagnostics.values():
        for variant in manifest["variants"]:
            source = (content / "queries" / variant["sql_file"]).resolve()
            source.relative_to((content / "queries").resolve())
            assert source.is_file()


def test_sql_normalizer_retains_raw_values_and_computational_to_string() -> None:
    source = (
        "SELECT round(elapsed, 2) AS elapsed, toString(replica_state) AS replica_state, "
        "concat(toString(shard), host) AS identity FROM system.test"
    )
    normalized = normalize_sql(source)
    assert "round(" not in normalized
    assert "elapsed AS elapsed" in normalized
    assert "replica_state AS replica_state" in normalized
    assert "concat(toString(shard), host)" in normalized
    assert normalize_sql(normalized) == normalized
