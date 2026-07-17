from __future__ import annotations

import json
from pathlib import Path

import pytest

from ch_diag.cli import _parser, main
from ch_diag.config import resolve_cli_defaults


def test_config_environment_and_cli_precedence(tmp_path: Path) -> None:
    config = tmp_path / "ch_diag.toml"
    config.write_text(
        """
[connection]
host = "config-host"
port = 9001
user = "config-user"

[collection]
mode = "remote-db-only"
target_scope = "cluster"
item_ids = ["overview.server"]

[output]
formats = ["json"]

[snapshots]
duration = 20
interval = 2
""".strip(),
        encoding="utf-8",
    )
    defaults = resolve_cli_defaults(
        str(config),
        {"CH_DIAG_HOST": "environment-host", "CH_DIAG_PORT": "9002"},
    )
    args = _parser(defaults).parse_args(
        [
            "--config",
            str(config),
            "snapshots",
            "--host",
            "cli-host",
            "--duration",
            "4",
            "--output-format",
            "html",
        ]
    )
    assert args.host == "cli-host"
    assert args.port == 9002
    assert args.user == "config-user"
    assert args.collection_mode == "remote-db-only"
    assert args.target_scope == "cluster"
    assert args.item_ids == ["overview.server"]
    assert args.output_format == ["html"]
    assert args.duration == 4
    assert args.interval == 2


def test_config_rejects_unknown_and_secret_keys(tmp_path: Path) -> None:
    config = tmp_path / "bad.toml"
    config.write_text('[connection]\npassword = "must-not-live-here"\n', encoding="utf-8")
    with pytest.raises(ValueError, match="unknown key"):
        resolve_cli_defaults(str(config), {})


def test_explain_plan_reports_nearest_preceding_lts(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["explain-plan", "--ch-version", "22.9.3.1"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["server_version"] == "22.9.3.1"
    assert payload["sql_compatibility_lts"] == "22.8"
