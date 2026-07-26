"""Explicit key-or-agent SSH transport with mandatory known_hosts verification."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import stat
from typing import Any

from .errors import ChDiagError
from .host import CommandResult


def _asyncssh():
    try:
        import asyncssh  # type: ignore
    except ModuleNotFoundError as exc:
        raise ChDiagError(
            "asyncssh is not installed; install the ch-diag package dependencies"
        ) from exc
    return asyncssh


@dataclass(frozen=True)
class SshConfig:
    host: str
    username: str
    known_hosts: str
    client_key: str | None = None
    agent_path: str | None = None
    port: int = 22
    connect_timeout: float = 10.0

    def validate(self) -> None:
        if not self.host or not self.username:
            raise ValueError("SSH host and username are required")
        if bool(self.client_key) == bool(self.agent_path):
            raise ValueError("SSH requires exactly one private key or agent socket")
        if self.client_key:
            key_path = Path(self.client_key).expanduser()
            if not key_path.is_file():
                raise ValueError(f"SSH private key file does not exist: {key_path}")
        if self.agent_path:
            agent_path = Path(self.agent_path).expanduser()
            try:
                mode = agent_path.stat().st_mode
            except OSError as exc:
                raise ValueError(f"SSH agent socket is not available: {agent_path}") from exc
            if not stat.S_ISSOCK(mode):
                raise ValueError(f"SSH_AUTH_SOCK is not a socket: {agent_path}")
        known_hosts = Path(self.known_hosts).expanduser()
        if not known_hosts.is_file():
            raise ValueError(f"known_hosts file does not exist: {known_hosts}")


class SshSession:
    def __init__(self, config: SshConfig, connection: Any) -> None:
        self.config = config
        self._connection = connection
        self._listener: Any | None = None

    @classmethod
    async def connect(cls, config: SshConfig) -> "SshSession":
        config.validate()
        asyncssh = _asyncssh()
        client_keys = (
            [str(Path(config.client_key).expanduser())] if config.client_key else []
        )
        agent_path = (
            str(Path(config.agent_path).expanduser()) if config.agent_path else None
        )
        try:
            connection = await asyncssh.connect(
                config.host,
                port=config.port,
                username=config.username,
                client_keys=client_keys,
                known_hosts=str(Path(config.known_hosts).expanduser()),
                config=None,
                preferred_auth=["publickey"],
                password_auth=False,
                kbdint_auth=False,
                agent_path=agent_path,
                agent_forwarding=False,
                connect_timeout=config.connect_timeout,
            )
        except Exception as exc:
            raise ChDiagError(f"SSH connection failed: {type(exc).__name__}: {exc}") from exc
        return cls(config, connection)

    async def open_tunnel(self, remote_host: str, remote_port: int) -> tuple[str, int]:
        if self._listener is not None:
            raise ChDiagError("SSH database tunnel is already open")
        self._listener = await self._connection.forward_local_port(
            "127.0.0.1",
            0,
            remote_host,
            remote_port,
        )
        return "127.0.0.1", int(self._listener.get_port())

    async def hostname(self) -> str:
        result = await self.run_script("hostname\n", timeout=2.0)
        return result.stdout.strip() or self.config.host

    async def run_script(self, script: str, *, timeout: float) -> CommandResult:
        try:
            result = await self._connection.run(
                "/bin/sh -s",
                input=script,
                check=False,
                timeout=timeout,
            )
        except TimeoutError:
            raise
        except Exception as exc:
            raise ChDiagError(f"SSH command failed: {type(exc).__name__}: {exc}") from exc
        return CommandResult(
            stdout=str(result.stdout),
            stderr=str(result.stderr),
            returncode=int(result.exit_status),
        )

    async def close(self) -> None:
        if self._listener is not None:
            self._listener.close()
            await self._listener.wait_closed()
            self._listener = None
        self._connection.close()
        await self._connection.wait_closed()

    async def __aenter__(self) -> "SshSession":
        return self

    async def __aexit__(self, _exc_type: Any, _exc: Any, _tb: Any) -> None:
        await self.close()
