from __future__ import annotations

import pytest

from ch_diag.versioning import ClickHouseVersion, select_variant


def test_clickhouse_version_uses_numeric_tuple_ordering() -> None:
    assert ClickHouseVersion.parse("25.10.2.4") > ClickHouseVersion.parse("25.9.99.99")
    assert ClickHouseVersion.parse("21.11") == ClickHouseVersion(21, 11, 0, 0)


def test_variant_ranges_are_half_open_and_scope_specific() -> None:
    variants = [
        {"id": "old", "min_ch_version": "20.3", "max_ch_version": "21.1", "scopes": ["node"]},
        {"id": "new", "min_ch_version": "21.1", "scopes": ["node"]},
        {"id": "cluster", "min_ch_version": "20.3", "scopes": ["cluster"]},
    ]
    assert select_variant(variants, ClickHouseVersion.parse("21.1"), "node")["id"] == "new"
    assert select_variant(variants, ClickHouseVersion.parse("25.8"), "cluster")["id"] == "cluster"


def test_overlapping_variants_fail_closed() -> None:
    variants = [
        {"id": "a", "min_ch_version": "20.3", "scopes": ["node"]},
        {"id": "b", "min_ch_version": "21.1", "scopes": ["node"]},
    ]
    with pytest.raises(ValueError, match="overlapping"):
        select_variant(variants, ClickHouseVersion.parse("25.8"), "node")
