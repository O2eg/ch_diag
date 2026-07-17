from __future__ import annotations

import json
from pathlib import Path

import yaml

from tools.report_review.config import ROOT, load_review_config
from tools.report_review.matrix import ReportCase, build_cases, build_command, validate_report
from tools.report_review.workload import ReviewWorkload


def test_default_review_configuration_covers_complete_matrix() -> None:
    config = load_review_config()
    cases = build_cases(config)

    assert len(cases) == 12
    assert {case.mode for case in cases} == {"local", "remote", "remote-db-only"}
    assert {case.scope for case in cases} == {"node", "cluster"}
    assert {case.run_type for case in cases} == {"one-shot", "snapshots"}
    assert config.fixture.compose_file == ROOT / "tests/integration/multinode/compose.yaml"
    assert config.workload.enabled is True
    assert config.workload.database == "chdiag_review"


def test_review_commands_keep_mode_specific_credentials_and_snapshot_options(tmp_path: Path) -> None:
    config = load_review_config()
    remote = build_command(
        config, ReportCase("remote", "cluster", "snapshots"), tmp_path / "remote"
    )
    db_only = build_command(
        config,
        ReportCase("remote-db-only", "node", "one-shot"),
        tmp_path / "db-only",
    )

    assert "--ssh-key" in remote
    assert "--cluster-name" in remote
    assert "--tags" not in remote
    assert remote[remote.index("--duration") + 1] == "10.0"
    assert "--ssh-key" not in db_only
    assert "--cluster-name" not in db_only
    assert "--duration" not in db_only


def test_review_compose_overlay_mounts_disposable_authorized_keys() -> None:
    overlay = yaml.safe_load(
        (ROOT / "tools/report_review/compose.review.yaml").read_text(encoding="utf-8")
    )

    for service in ("node1", "node2"):
        volumes = overlay["services"][service]["volumes"]
        assert len(volumes) == 1
        assert "CHDIAG_REVIEW_AUTHORIZED_KEYS" in volumes[0]
        assert volumes[0].endswith(":/test-ssh/authorized_keys:ro")


def test_report_validation_checks_artifact_html_and_summarizes_statuses(
    tmp_path: Path,
) -> None:
    config = load_review_config()
    config = config.__class__(
        **{
            **config.__dict__,
            "runtime": config.runtime.__class__(
                **{**config.runtime.__dict__, "browser_validation": False}
            ),
        }
    )
    artifact = {
        "artifact_schema_version": 5,
        "generator": {},
        "content": {},
        "report": {},
        "database": {},
        "target": {},
        "runtime": {},
        "display": {},
        "sections": [{"items": ["item.ok", "item.empty"]}],
        "items": {
            "item.ok": {
                "collection_status": "ok",
                "result": {"kind": "none"},
            },
            "item.empty": {
                "collection_status": "empty",
                "result": {"kind": "none"},
            },
        },
        "query_texts": {},
        "snapshot_schemas": {},
        "snapshots": [{"sample": 0}],
        "diagnostics": [{"code": "sample_skipped_source_busy"}],
    }
    (tmp_path / "report.json").write_text(json.dumps(artifact), encoding="utf-8")
    (tmp_path / "report.html").write_text(
        '<!doctype html><script id="ch-diag-artifact" type="application/json">'
        '{"artifact_schema_version":5}</script>',
        encoding="utf-8",
    )

    result = validate_report(config, tmp_path)

    assert result["collection_statuses"] == {"empty": 1, "ok": 1}
    assert result["diagnostic_codes"] == {"sample_skipped_source_busy": 1}
    assert result["charts_without_data"] == []
    assert result["snapshot_count"] == 1
    assert result["browser"]["status"] == "skipped"


def test_review_workload_uses_only_dedicated_database_and_bounded_batches() -> None:
    config = load_review_config()
    workload = ReviewWorkload(config)
    query = workload._insert_query(config.workload.database)

    assert "INSERT INTO chdiag_review.distributed_events" in query
    assert "FROM numbers(%(rows)s)" in query
    assert "insert_distributed_sync = 1" in query
    assert config.workload.insert_rows_per_batch < config.workload.seed_rows
