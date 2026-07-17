from __future__ import annotations

import pytest

from ch_diag.versioning import (
    ClickHouseVersion,
    parse_lts_branch,
    resolve_lts_branch,
    select_variant,
)


def test_clickhouse_version_uses_numeric_tuple_ordering() -> None:
    assert ClickHouseVersion.parse("25.10.2.4") > ClickHouseVersion.parse("25.9.99.99")
    assert ClickHouseVersion.parse("21.11") == ClickHouseVersion(21, 11, 0, 0)
    assert ClickHouseVersion.parse("25.8.28.1").branch == "25.8"
    assert parse_lts_branch("25.8") == ClickHouseVersion(25, 8)
    with pytest.raises(ValueError, match="LTS branch"):
        parse_lts_branch("25.8.1")


def test_variant_selection_is_lts_branch_and_scope_specific() -> None:
    variants = [
        {"id": "old", "lts_versions": ["20.3", "20.8"], "scopes": ["node"]},
        {"id": "new", "lts_versions": ["21.3", "21.8"], "scopes": ["node"]},
        {"id": "cluster", "lts_versions": ["20.3", "20.8"], "scopes": ["cluster"]},
    ]
    assert select_variant(variants, ClickHouseVersion.parse("21.3.20.1"), "node")["id"] == "new"
    assert select_variant(variants, ClickHouseVersion.parse("20.8.18.32"), "cluster")["id"] == "cluster"
    assert select_variant(variants, ClickHouseVersion.parse("21.4"), "node")["id"] == "new"


@pytest.mark.parametrize(
    ("server_version", "expected_lts"),
    [
        ("20.3.21.2", "20.3"),
        ("20.7", "20.3"),
        ("20.8.18.32", "20.8"),
        ("22.4", "22.3"),
        ("22.9", "22.8"),
        ("25.1", "24.8"),
        ("26.8", "26.3"),
    ],
)
def test_server_version_resolves_to_nearest_preceding_lts(
    server_version: str,
    expected_lts: str,
) -> None:
    supported = [
        "20.3",
        "20.8",
        "21.3",
        "21.8",
        "22.3",
        "22.8",
        "24.8",
        "26.3",
    ]
    assert resolve_lts_branch(ClickHouseVersion.parse(server_version), supported) == expected_lts


def test_server_older_than_first_lts_has_no_compatibility_anchor() -> None:
    assert resolve_lts_branch(ClickHouseVersion.parse("20.2"), ["20.3", "20.8"]) is None


def test_overlapping_variants_fail_closed() -> None:
    variants = [
        {"id": "a", "lts_versions": ["25.8"], "scopes": ["node"]},
        {"id": "b", "lts_versions": ["25.8"], "scopes": ["node"]},
    ]
    with pytest.raises(ValueError, match="overlapping"):
        select_variant(variants, ClickHouseVersion.parse("25.8"), "node")
