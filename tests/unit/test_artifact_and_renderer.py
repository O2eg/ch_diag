from __future__ import annotations

import json

from jsonschema import Draft202012Validator

from ch_diag.artifact_schema import load_artifact_schema
from ch_diag.clickhouse import column_descriptor, json_safe
from ch_diag.render.html import render_html


def test_large_clickhouse_integer_is_lossless() -> None:
    descriptor = column_descriptor("rows", "UInt64", [], 0)
    assert json_safe(2**64 - 1, descriptor) == str(2**64 - 1)


def test_numeric_hash_is_an_exact_identifier_not_an_adaptive_count() -> None:
    descriptor = column_descriptor("normalized_query_hash", "UInt64", [], 0)

    assert descriptor["value_kind"] == "integer"
    assert descriptor["semantic_role"] == "identifier"
    assert descriptor["quantity"] == "identifier"
    assert descriptor["unit"] == "none"
    assert json_safe(11636551938543030549, descriptor) == "11636551938543030549"


def test_packaged_artifact_json_schema_is_v5() -> None:
    schema = load_artifact_schema()
    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["properties"]["artifact_schema_version"] == {"const": 5}
    assert "column" in schema["$defs"]


def test_renderer_is_standalone_and_branded_for_ch_diag() -> None:
    artifact = {
        "artifact_schema_version": 5,
        "generator": {"name": "ch_diag", "product": "ch_diag", "version": "0.8.0"},
        "content": {"schema_version": 5, "document": {"catalogs": {"presentation": {"units": {}}}}, "provenance": {}},
        "report": {"id": "ch_diag", "title": "ClickHouse Diagnostic Report"},
        "database": {"engine": "clickhouse", "server_version": "25.8"},
        "target": {
            "execution_scope": "node",
            "cluster_name": None,
            "connection_endpoint": {"host": "127.0.0.1", "port": 9000},
            "host_scope": "collector",
        },
        "runtime": {"mode": "one-shot", "collection_mode": "remote-db-only"},
        "display": {},
        "sections": [],
        "items": {},
        "query_texts": {},
        "snapshot_schemas": {},
        "snapshots": [],
        "diagnostics": [],
    }
    html = render_html(artifact)
    assert "cdn.jsdelivr" not in html
    assert "unpkg.com" not in html
    assert "echarts" in html.casefold()
    assert "github.com/O2eg/ch_diag" in html
    assert "pg_diag" not in html
    assert json.dumps(artifact, ensure_ascii=False) not in html


def test_formal_schema_is_valid_and_accepts_the_renderer_artifact() -> None:
    schema = load_artifact_schema()
    Draft202012Validator.check_schema(schema)
    artifact = {
        "artifact_schema_version": 5,
        "generator": {"name": "ch_diag", "product": "ch_diag", "version": "0.8.0"},
        "content": {"schema_version": 5},
        "report": {"id": "ch_diag", "title": "ClickHouse Diagnostic Report"},
        "database": {"engine": "clickhouse", "server_version": "25.8"},
        "target": {
            "execution_scope": "node",
            "cluster_name": None,
            "connection_endpoint": {"host": "127.0.0.1", "port": 9000},
            "host_scope": "collector",
        },
        "runtime": {"mode": "one-shot", "collection_mode": "remote-db-only"},
        "display": {},
        "sections": [],
        "items": {},
        "query_texts": {},
        "snapshot_schemas": {},
        "snapshots": [],
        "diagnostics": [],
    }
    Draft202012Validator(schema).validate(artifact)
