#!/usr/bin/env python3
"""Build, seed and test the reusable two-replica ClickHouse+Keeper fixture."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import time


COMPOSE_FILE = Path("tests/integration/multinode/compose.yaml")
PROJECT_NAME = "chdiag-multinode"
NODES = ("chdiag-multinode-node1", "chdiag-multinode-node2")
KEEPER = "chdiag-multinode-keeper"


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
        check=check,
        text=True,
        capture_output=capture_output,
        input=input_text,
        env=env,
    )


def compose_command(*arguments: str) -> list[str]:
    return [
        "docker",
        "compose",
        "--project-name",
        PROJECT_NAME,
        "--file",
        str(COMPOSE_FILE),
        *arguments,
    ]


def wait_for_tcp(host: str, port: int, timeout_seconds: float) -> None:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        try:
            with socket.create_connection((host, port), timeout=1.0):
                return
        except OSError:
            time.sleep(1.0)
    raise RuntimeError(f"TCP endpoint {host}:{port} did not become ready")


def wait_for_node(container: str, timeout_seconds: float) -> None:
    deadline = time.monotonic() + timeout_seconds
    command = [
        "docker",
        "exec",
        container,
        "clickhouse-client",
        "--query",
        "SELECT 1",
    ]
    while time.monotonic() < deadline:
        result = _run(command, check=False, capture_output=True)
        if result.returncode == 0 and result.stdout.strip() == "1":
            print(f"READY {container}", flush=True)
            return
        time.sleep(2.0)
    raise RuntimeError(f"{container} did not become ready")


def execute_sql_file(container: str, path: Path) -> None:
    print(f"APPLY {path.name} on {container}", flush=True)
    _run(
        ["docker", "exec", "--interactive", container, "clickhouse-client", "--multiquery"],
        input_text=path.read_text(encoding="utf-8"),
    )


def execute_query(container: str, query: str) -> None:
    _run(["docker", "exec", container, "clickhouse-client", "--query", query])


def seed_fixture(root: Path) -> None:
    fixture = root / "tests" / "integration" / "multinode"
    execute_sql_file(NODES[0], fixture / "fixture-ddl.sql")
    execute_sql_file(NODES[0], fixture / "fixture-node1.sql")
    execute_sql_file(NODES[1], fixture / "fixture-node2.sql")
    execute_query(NODES[0], "SYSTEM FLUSH DISTRIBUTED chdiag_fixture.distributed_events")
    for node in NODES:
        execute_query(node, "SYSTEM SYNC REPLICA chdiag_fixture.replicated_events")
        execute_query(node, "SYSTEM FLUSH LOGS")


def run_tests(root: Path) -> None:
    environment = os.environ.copy()
    environment.update(
        {
            "CH_DIAG_TEST_HOST": "127.0.0.1",
            "CH_DIAG_TEST_PORT": os.environ.get("CHDIAG_NODE1_NATIVE_PORT", "19101"),
            "CH_DIAG_TEST_NODE2_PORT": os.environ.get("CHDIAG_NODE2_NATIVE_PORT", "19102"),
            "CH_DIAG_TEST_CLUSTER": "chdiag_cluster",
        }
    )
    _run(
        [
            sys.executable,
            "-m",
            "pytest",
            "-q",
            "tests/integration/test_multinode_clickhouse.py",
            "tests/integration/test_live_clickhouse.py",
        ],
        env=environment,
    )


def show_logs() -> None:
    for container in (KEEPER, *NODES):
        print(f"--- logs: {container} ---", file=sys.stderr)
        _run(["docker", "logs", "--tail", "200", container], check=False)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--no-build", action="store_true", help="reuse the existing custom image")
    parser.add_argument("--skip-tests", action="store_true", help="only start and seed the fixture")
    parser.add_argument(
        "--remove",
        action="store_true",
        help="remove containers and named test volumes after the run",
    )
    parser.add_argument("--startup-timeout", type=float, default=180.0)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if shutil.which("docker") is None:
        print("ERROR docker executable is required", file=sys.stderr)
        return 2

    root = Path(__file__).resolve().parents[1]
    os.chdir(root)
    up = ["up", "--detach"]
    if not args.no_build:
        up.append("--build")
    failed = False
    try:
        _run(compose_command(*up))
        keeper_port = int(os.environ.get("CHDIAG_KEEPER_PORT", "19181"))
        wait_for_tcp("127.0.0.1", keeper_port, args.startup_timeout)
        for node in NODES:
            wait_for_node(node, args.startup_timeout)
        seed_fixture(root)
        if not args.skip_tests:
            run_tests(root)
        print("PASS multi-node ClickHouse+Keeper fixture", flush=True)
    except (OSError, RuntimeError, subprocess.CalledProcessError, ValueError) as exc:
        failed = True
        print(f"FAIL multi-node ClickHouse+Keeper fixture: {exc}", file=sys.stderr)
        show_logs()
    finally:
        if args.remove:
            _run(compose_command("down", "--volumes"), check=False)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
