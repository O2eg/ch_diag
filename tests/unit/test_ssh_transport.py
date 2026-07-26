from __future__ import annotations

import asyncio
from pathlib import Path
import socket
from typing import Any

import pytest

from ch_diag.ssh_transport import SshConfig, SshSession


class _FakeConnection:
    pass


def _known_hosts(tmp_path: Path) -> Path:
    path = tmp_path / "known_hosts"
    path.write_text("db.example ssh-ed25519 placeholder\n", encoding="utf-8")
    return path


def test_agent_socket_must_be_a_unix_socket(tmp_path: Path) -> None:
    agent_path = tmp_path / "agent.sock"
    agent_path.write_text("not a socket", encoding="utf-8")
    config = SshConfig(
        host="db.example",
        username="chdiag",
        known_hosts=str(_known_hosts(tmp_path)),
        agent_path=str(agent_path),
    )

    with pytest.raises(ValueError, match="SSH_AUTH_SOCK is not a socket"):
        config.validate()


def test_asyncssh_uses_agent_without_forwarding(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, dict[str, Any]]] = []
    agent_path = tmp_path / "agent.sock"

    class FakeAsyncssh:
        @staticmethod
        async def connect(host: str, **kwargs: Any) -> _FakeConnection:
            calls.append((host, kwargs))
            return _FakeConnection()

    monkeypatch.setattr("ch_diag.ssh_transport._asyncssh", lambda: FakeAsyncssh)
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as agent:
        agent.bind(str(agent_path))
        config = SshConfig(
            host="db.example",
            username="chdiag",
            known_hosts=str(_known_hosts(tmp_path)),
            agent_path=str(agent_path),
        )
        session = asyncio.run(SshSession.connect(config))

    assert session.config is config
    _, options = calls[0]
    assert options["client_keys"] == []
    assert options["agent_path"] == str(agent_path)
    assert options["agent_forwarding"] is False
    assert options["config"] is None
    assert options["preferred_auth"] == ["publickey"]
    assert options["password_auth"] is False
    assert options["kbdint_auth"] is False


def test_key_mode_disables_agent_fallback(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, dict[str, Any]]] = []
    key = tmp_path / "id_ed25519"
    key.write_text("test key\n", encoding="utf-8")

    class FakeAsyncssh:
        @staticmethod
        async def connect(host: str, **kwargs: Any) -> _FakeConnection:
            calls.append((host, kwargs))
            return _FakeConnection()

    monkeypatch.setattr("ch_diag.ssh_transport._asyncssh", lambda: FakeAsyncssh)
    config = SshConfig(
        host="db.example",
        username="chdiag",
        known_hosts=str(_known_hosts(tmp_path)),
        client_key=str(key),
    )

    asyncio.run(SshSession.connect(config))

    _, options = calls[0]
    assert options["client_keys"] == [str(key)]
    assert options["agent_path"] is None
    assert options["agent_forwarding"] is False
