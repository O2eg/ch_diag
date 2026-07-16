from __future__ import annotations

from pathlib import Path

import yaml

from tools.normalize_sql_outputs import normalize_sql
from tools.run_legacy_clickhouse_matrix import LEGACY_IMAGES, compatible_architecture


def test_legacy_boundary_matrix_is_complete_and_pinned() -> None:
    assert list(LEGACY_IMAGES) == ["20.3", "20.11", "21.1", "21.4", "21.8", "21.11", "22.2"]
    assert len({item.host_port for item in LEGACY_IMAGES.values()}) == len(LEGACY_IMAGES)
    assert len({item.container_name for item in LEGACY_IMAGES.values()}) == len(LEGACY_IMAGES)
    for item in LEGACY_IMAGES.values():
        assert item.version.startswith(item.boundary + ".")
        assert item.digest.startswith("sha256:")
        assert len(item.digest) == len("sha256:") + 64
        assert "@sha256:" in item.reference


def test_legacy_architecture_gate() -> None:
    assert compatible_architecture("x86_64")
    assert compatible_architecture("AMD64")
    assert not compatible_architecture("aarch64")
    assert not compatible_architecture("arm64")


def test_supported_legacy_sql_is_self_contained_in_the_content_pack() -> None:
    repo = Path(__file__).resolve().parents[2]
    assert not (repo / "sql").exists()
    assert not (repo / "template").exists()

    content = repo / "ch_diag" / "content"
    queries = yaml.safe_load((content / "queries.yaml").read_text(encoding="utf-8"))[
        "queries"
    ]
    legacy = {
        query_id: manifest
        for query_id, manifest in queries.items()
        if manifest.get("legacy_item_id")
    }
    assert len(legacy) == 55
    for manifest in legacy.values():
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
