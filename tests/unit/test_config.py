from __future__ import annotations

import json
from pathlib import Path
import socket

import pytest

from ch_diag.cli import _parser, _ssh_config, main
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


def test_cli_key_overrides_agent_from_config(tmp_path: Path) -> None:
    config = tmp_path / "ch_diag.toml"
    config.write_text(
        """
[ssh]
host = "db.example"
user = "chdiag"
agent = true
known_hosts = "/secure/known_hosts"
""".strip(),
        encoding="utf-8",
    )

    args = _parser(resolve_cli_defaults(str(config), {})).parse_args(
        ["one-shot", "--ssh-key", "/secure/id_ed25519"]
    )

    assert args.ssh_key == "/secure/id_ed25519"
    assert args.ssh_agent is False


def test_cli_agent_overrides_key_from_config(tmp_path: Path) -> None:
    config = tmp_path / "ch_diag.toml"
    config.write_text(
        """
[ssh]
host = "db.example"
user = "chdiag"
key = "/secure/id_ed25519"
known_hosts = "/secure/known_hosts"
""".strip(),
        encoding="utf-8",
    )

    args = _parser(resolve_cli_defaults(str(config), {})).parse_args(
        ["one-shot", "--ssh-agent"]
    )

    assert args.ssh_key is None
    assert args.ssh_agent is True


def test_environment_agent_overrides_toml_key(tmp_path: Path) -> None:
    config = tmp_path / "ch_diag.toml"
    config.write_text(
        """
[ssh]
host = "db.example"
user = "chdiag"
key = "/secure/id_ed25519"
known_hosts = "/secure/known_hosts"
""".strip(),
        encoding="utf-8",
    )

    defaults = resolve_cli_defaults(
        str(config),
        {"CH_DIAG_SSH_AGENT": "true"},
    )

    assert defaults["ssh_agent"] is True
    assert defaults["ssh_key"] is None


def test_config_rejects_key_and_agent_together(tmp_path: Path) -> None:
    config = tmp_path / "ch_diag.toml"
    config.write_text(
        '[ssh]\nkey = "/secure/id_ed25519"\nagent = true\n',
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="either key or agent"):
        resolve_cli_defaults(str(config), {})


def test_ssh_agent_uses_inherited_socket(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    known_hosts = tmp_path / "known_hosts"
    known_hosts.write_text("db.example ssh-ed25519 placeholder\n", encoding="utf-8")
    agent_path = tmp_path / "agent.sock"

    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as agent:
        agent.bind(str(agent_path))
        monkeypatch.setenv("SSH_AUTH_SOCK", str(agent_path))
        args = _parser().parse_args(
            [
                "one-shot",
                "--ssh-host",
                "db.example",
                "--ssh-user",
                "chdiag",
                "--ssh-agent",
                "--ssh-known-hosts",
                str(known_hosts),
            ]
        )
        config = _ssh_config(args)

    assert config is not None
    assert config.client_key is None
    assert config.agent_path == str(agent_path)


def test_ssh_agent_requires_ssh_auth_sock(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SSH_AUTH_SOCK", raising=False)
    args = _parser().parse_args(
        [
            "one-shot",
            "--ssh-host",
            "db.example",
            "--ssh-user",
            "chdiag",
            "--ssh-agent",
            "--ssh-known-hosts",
            "/secure/known_hosts",
        ]
    )

    with pytest.raises(ValueError, match="SSH_AUTH_SOCK"):
        _ssh_config(args)


def test_explain_plan_reports_nearest_preceding_lts(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["explain-plan", "--ch-version", "22.9.3.1"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["server_version"] == "22.9.3.1"
    assert payload["sql_compatibility_lts"] == "22.8"
