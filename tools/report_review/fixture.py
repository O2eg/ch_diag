"""Lifecycle for the reusable multi-node ClickHouse review fixture."""

from __future__ import annotations

import os
from pathlib import Path
import shutil
import socket
import subprocess
import time

from .config import ROOT, ReviewConfig


class FixtureError(RuntimeError):
    """The managed or external review fixture is not usable."""


def _run(
    command: list[str],
    *,
    check: bool = True,
    capture_output: bool = False,
    input_text: str | None = None,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=ROOT,
        check=check,
        text=True,
        capture_output=capture_output,
        input=input_text,
        env=env,
    )


def wait_for_tcp(host: str, port: int, timeout_seconds: float) -> None:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        try:
            with socket.create_connection((host, port), timeout=1.0):
                return
        except OSError:
            time.sleep(1.0)
    raise FixtureError(f"TCP endpoint {host}:{port} did not become ready")


class ReviewFixture:
    def __init__(self, config: ReviewConfig) -> None:
        self.config = config
        self._authorized_keys = config.fixture.state_directory / "authorized_keys"

    def _compose_environment(self) -> dict[str, str]:
        fixture = self.config.fixture
        environment = os.environ.copy()
        environment.update(
            {
                "CHDIAG_KEEPER_PORT": str(fixture.keeper_port),
                "CHDIAG_NODE1_NATIVE_PORT": str(fixture.node1_port),
                "CHDIAG_NODE2_NATIVE_PORT": str(fixture.node2_port),
                "CHDIAG_NODE1_SSH_PORT": str(fixture.node1_ssh_port),
                "CHDIAG_NODE2_SSH_PORT": str(fixture.node2_ssh_port),
                "CHDIAG_REVIEW_AUTHORIZED_KEYS": str(self._authorized_keys),
            }
        )
        return environment

    def _compose_command(self, *arguments: str) -> list[str]:
        fixture = self.config.fixture
        return [
            "docker",
            "compose",
            "--project-name",
            fixture.project_name,
            "--file",
            str(fixture.compose_file),
            "--file",
            str(fixture.compose_overlay),
            *arguments,
        ]

    def _require_managed_prerequisites(self) -> None:
        required = {
            "docker": shutil.which("docker"),
            "ssh-keygen": shutil.which("ssh-keygen"),
            "ssh-keyscan": shutil.which("ssh-keyscan"),
        }
        missing = sorted(name for name, path in required.items() if path is None)
        if missing:
            raise FixtureError("missing fixture prerequisite(s): " + ", ".join(missing))
        for path in (self.config.fixture.compose_file, self.config.fixture.compose_overlay):
            if not path.is_file():
                raise FixtureError(f"fixture file does not exist: {path}")

    def _ensure_ssh_key(self) -> None:
        key = self.config.ssh.key
        key.parent.mkdir(parents=True, exist_ok=True)
        self._authorized_keys.parent.mkdir(parents=True, exist_ok=True)
        if not key.is_file():
            _run(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(key)])
        public = _run(
            ["ssh-keygen", "-y", "-f", str(key)], capture_output=True
        ).stdout.strip()
        if not public:
            raise FixtureError(f"cannot derive public key from {key}")
        self._authorized_keys.write_text(public + "\n", encoding="utf-8")
        key.chmod(0o600)
        self._authorized_keys.chmod(0o600)

    def _wait_for_node(self, container: str) -> None:
        deadline = time.monotonic() + self.config.fixture.startup_timeout_seconds
        command = ["docker", "exec", container, "clickhouse-client", "--query", "SELECT 1"]
        while time.monotonic() < deadline:
            result = _run(command, check=False, capture_output=True)
            if result.returncode == 0 and result.stdout.strip() == "1":
                print(f"READY {container}", flush=True)
                return
            time.sleep(2.0)
        raise FixtureError(f"ClickHouse container {container} did not become ready")

    def _execute_sql_file(self, container: str, path: Path) -> None:
        print(f"APPLY {path.name} on {container}", flush=True)
        _run(
            ["docker", "exec", "--interactive", container, "clickhouse-client", "--multiquery"],
            input_text=path.read_text(encoding="utf-8"),
        )

    def _execute_query(self, container: str, query: str) -> None:
        _run(["docker", "exec", container, "clickhouse-client", "--query", query])

    def _seed(self) -> None:
        fixture = ROOT / "tests" / "integration" / "multinode"
        node1 = self.config.fixture.node1_container
        node2 = self.config.fixture.node2_container
        self._execute_sql_file(node1, fixture / "fixture-ddl.sql")
        self._execute_sql_file(node1, fixture / "fixture-node1.sql")
        self._execute_sql_file(node2, fixture / "fixture-node2.sql")
        self._execute_query(
            node1, "SYSTEM FLUSH DISTRIBUTED chdiag_fixture.distributed_events"
        )
        for node in (node1, node2):
            self._execute_query(node, "SYSTEM SYNC REPLICA chdiag_fixture.replicated_events")
            self._execute_query(node, "SYSTEM FLUSH LOGS")

    def _scan_known_hosts(self) -> None:
        ssh = self.config.ssh
        deadline = time.monotonic() + self.config.fixture.startup_timeout_seconds
        while time.monotonic() < deadline:
            result = _run(
                [
                    "ssh-keyscan",
                    "-p",
                    str(ssh.port),
                    "-t",
                    "ed25519",
                    ssh.host,
                ],
                check=False,
                capture_output=True,
            )
            if result.returncode == 0 and result.stdout.strip():
                ssh.known_hosts.parent.mkdir(parents=True, exist_ok=True)
                ssh.known_hosts.write_text(result.stdout, encoding="utf-8")
                ssh.known_hosts.chmod(0o600)
                return
            time.sleep(1.0)
        raise FixtureError(f"SSH endpoint {ssh.host}:{ssh.port} did not expose a host key")

    def prepare(self) -> None:
        fixture = self.config.fixture
        if not fixture.manage:
            wait_for_tcp(
                self.config.database.host,
                self.config.database.port,
                fixture.startup_timeout_seconds,
            )
            if "remote" in self.config.matrix.modes:
                for path in (self.config.ssh.key, self.config.ssh.known_hosts):
                    if not path.is_file():
                        raise FixtureError(f"external SSH credential does not exist: {path}")
                wait_for_tcp(
                    self.config.ssh.host,
                    self.config.ssh.port,
                    fixture.startup_timeout_seconds,
                )
            print("READY external review fixture", flush=True)
            return

        self._require_managed_prerequisites()
        self._ensure_ssh_key()
        up = ["up", "--detach"]
        if fixture.build:
            up.append("--build")
        else:
            up.append("--no-build")
        _run(self._compose_command(*up), env=self._compose_environment())
        wait_for_tcp("127.0.0.1", fixture.keeper_port, fixture.startup_timeout_seconds)
        self._wait_for_node(fixture.node1_container)
        self._wait_for_node(fixture.node2_container)
        if fixture.seed:
            self._seed()
        if "remote" in self.config.matrix.modes:
            self._scan_known_hosts()
        print("READY managed multi-node review fixture", flush=True)

    def show_logs(self) -> None:
        if not self.config.fixture.manage or shutil.which("docker") is None:
            return
        for container in (
            self.config.fixture.keeper_container,
            self.config.fixture.node1_container,
            self.config.fixture.node2_container,
        ):
            print(f"--- logs: {container} ---", flush=True)
            _run(["docker", "logs", "--tail", "100", container], check=False)

    def close(self) -> None:
        if not (self.config.fixture.manage and self.config.fixture.cleanup):
            return
        _run(
            self._compose_command("down", "--volumes"),
            check=False,
            env=self._compose_environment(),
        )
