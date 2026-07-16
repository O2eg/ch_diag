from __future__ import annotations

from pathlib import Path

import pytest

from ch_diag.cli import _parser
from ch_diag.config import resolve_cli_defaults
from ch_diag import legacy_cli


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


def test_legacy_cli_translates_to_modern_collector(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: list[str] = []

    def modern(arguments: list[str]) -> int:
        captured.extend(arguments)
        return 0

    monkeypatch.setattr(legacy_cli, "modern_main", modern)
    assert legacy_cli.main(["--host", "db", "--cluster-name", "prod"]) == 0
    assert captured[:3] == ["one-shot", "--host", "db"]
    assert captured[captured.index("--target-scope") + 1] == "cluster"
    assert captured[captured.index("--cluster-name") + 1] == "prod"
    assert captured[captured.index("--output-format") + 1] == "html"
