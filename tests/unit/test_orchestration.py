from __future__ import annotations

import json
from pathlib import Path

import ch_diag.cli as cli_module
from ch_diag.cli import main
from ch_diag.orchestration import (
    EXIT_CODES,
    canonical_hash,
    capabilities,
    summarize_artifact,
    summarize_execution_plan,
)


def _artifact() -> dict[str, object]:
    return {
        "artifact_schema_version": 5,
        "generator": {"name": "ch_diag", "product": "ch_diag", "version": "test"},
        "content": {"schema_version": 5, "checksum": "sha256:test", "report_id": "ch_diag"},
        "report": {"id": "ch_diag", "title": "ClickHouse Diagnostic Report"},
        "database": {"engine": "clickhouse", "server_version": "25.8"},
        "target": {
            "execution_scope": "node",
            "cluster_name": None,
            "connection_endpoint": {"host": "127.0.0.1", "port": 9000},
            "host_scope": "collector",
        },
        "runtime": {
            "mode": "one-shot",
            "collection_mode": "remote-db-only",
            "completion_status": "succeeded",
            "collection_summary": {
                "total_items": 0,
                "successful_items": 0,
                "complete_items": 0,
                "failed_items": 0,
                "coverage_incomplete_items": 0,
                "completeness_ratio": 1.0,
            },
        },
        "display": {},
        "sections": [],
        "items": {},
        "query_texts": {},
        "snapshot_schemas": {},
        "snapshots": [],
        "diagnostics": [],
    }


def test_machine_hashes_and_summaries_are_deterministic() -> None:
    assert canonical_hash({"b": 2, "a": 1}) == canonical_hash({"a": 1, "b": 2})
    summary = summarize_artifact(_artifact())
    assert summary["schema_version"] == "ch_diag/summary-v1"
    assert summary["completeness"]["ratio"] == 1.0
    assert summary["fallback_items"]["count"] == 0

    plan = {
        "mode": "one-shot",
        "collection_mode": "remote-db-only",
        "target_scope": "node",
        "server_version": "25.8",
        "sql_compatibility_lts": "25.8",
        "items": [
            {
                "item_id": "overview.server",
                "status": "planned",
                "targets": ["database"],
                "fallback_item": None,
            }
        ],
    }
    plan_summary = summarize_execution_plan(plan)
    assert plan_summary["item_count"] == 1
    assert plan_summary["target_counts"] == {"database": 1}


def test_capability_document_exposes_stable_machine_contract() -> None:
    document = capabilities()
    assert document["capability_schema_version"] == "pg_play/capabilities/v1"
    assert document["contract_version"] == "pg_play/component/v1"
    assert document["component"] == "ch_diag"
    assert document["commands"]["summarize"]["machine_output"] is True
    assert document["artifact_schema_versions"] == [5]


def test_cli_summarize_validate_and_machine_envelope(
    tmp_path: Path,
    capsys,
) -> None:
    artifact_path = tmp_path / "report.json"
    artifact_path.write_text(json.dumps(_artifact()), encoding="utf-8")

    assert main(["summarize", str(artifact_path)]) == 0
    assert json.loads(capsys.readouterr().out)["schema_version"] == "ch_diag/summary-v1"

    assert main(["validate-artifact", str(artifact_path)]) == 0
    validated = json.loads(capsys.readouterr().out)
    assert validated["path"] == str(artifact_path)
    assert validated["hash"].startswith("sha256:")

    assert (
        main(
            [
                "--machine",
                "--request-id",
                "request-1",
                "summarize",
                str(artifact_path),
            ]
        )
        == EXIT_CODES["success"]
    )
    envelope = json.loads(capsys.readouterr().out)
    assert envelope["contract_version"] == "pg_play/component/v1"
    assert envelope["component"] == "ch_diag"
    assert envelope["request_id"] == "request-1"
    assert envelope["status"] == "succeeded"
    assert envelope["artifacts"][0]["kind"] == "DiagnosticReport"


def test_machine_capabilities_need_no_subcommand(capsys) -> None:
    assert main(["--machine", "--component-capabilities"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["command"] == "capabilities"
    assert payload["result"]["component"] == "ch_diag"


def test_machine_invalid_artifact_uses_validation_exit_code(
    tmp_path: Path,
    capsys,
) -> None:
    invalid = tmp_path / "invalid.json"
    invalid.write_text("{}", encoding="utf-8")

    assert (
        main(["--machine", "validate-artifact", str(invalid)])
        == EXIT_CODES["validation_error"]
    )
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "failed"
    assert payload["error"]["code"] == "validation_error"


def test_machine_collection_retains_artifact_and_uses_partial_exit_code(
    tmp_path: Path,
    capsys,
    monkeypatch,
) -> None:
    artifact = _artifact()
    artifact["runtime"]["completion_status"] = "partial"  # type: ignore[index]
    report = tmp_path / "report.json"
    report.write_text(json.dumps(artifact), encoding="utf-8")

    def partial_dispatch(args) -> int:
        artifact["runtime"]["output_json"] = str(report)  # type: ignore[index]
        args._collection_artifacts = [artifact]
        return 1

    monkeypatch.setattr(cli_module, "_dispatch", partial_dispatch)

    assert (
        main(
            [
                "--machine",
                "one-shot",
                "--collection-mode",
                "local",
                "--target-scope",
                "node",
            ]
        )
        == EXIT_CODES["partial"]
    )
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "partial"
    assert payload["artifacts"][0]["path"] == str(report)
    assert payload["error"]["code"] == "partial"
