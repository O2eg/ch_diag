#!/usr/bin/env python3
"""Run the real ClickHouse LTS SQL compatibility matrix.

The oldest public LTS images are linux/amd64 only.  On another architecture the
runner exits successfully with an explicit skip before pulling or starting a
container.  Containers are retained and reused by default for local iteration;
CI passes --remove to clean its ephemeral runner.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import time


@dataclass(frozen=True)
class LTSImage:
    branch: str
    repository: str
    version: str
    digest: str
    host_port: int

    @property
    def reference(self) -> str:
        return f"{self.repository}:{self.version}@{self.digest}"

    @property
    def container_name(self) -> str:
        return "chdiag-lts-" + self.branch.replace(".", "-")


LTS_IMAGES: dict[str, LTSImage] = {
    item.branch: item
    for item in (
        LTSImage(
            "20.3",
            "yandex/clickhouse-server",
            "20.3.21.2",
            "sha256:e9c704ac6dc7f11e09b3c00d784625ac6f7c4fe9c9050c1d4b61b572f2bdd434",
            19203,
        ),
        LTSImage(
            "20.8",
            "yandex/clickhouse-server",
            "20.8.18.32",
            "sha256:e193a420c28c1ea0f2148e22b0b86cd8876e3b9f15015caa11862961e90d1aaa",
            19208,
        ),
        LTSImage(
            "21.3",
            "yandex/clickhouse-server",
            "21.3.20.1",
            "sha256:4eccfffb01d735ab7c1af9a97fbff0c532112a6871b2bb5fe5c478d86d247b7e",
            19303,
        ),
        LTSImage(
            "21.8",
            "clickhouse/clickhouse-server",
            "21.8.15.7",
            "sha256:a9141f199e4b1f60cd6fe5ee58e25a86938117d26a73c4a1fa5c31b6e2f64abf",
            19308,
        ),
        LTSImage(
            "22.3",
            "clickhouse/clickhouse-server",
            "22.3.20.29",
            "sha256:f423f63c3d73f567a89cf919f61f38734e9df014f160826a22ffc3c730988218",
            19403,
        ),
        LTSImage(
            "22.8",
            "clickhouse/clickhouse-server",
            "22.8.21.38",
            "sha256:015a65bf1cef750052c2456dd41af853d8ca65417a3cc564a7577a15c21ad479",
            19408,
        ),
        LTSImage(
            "23.3",
            "clickhouse/clickhouse-server",
            "23.3.22.3",
            "sha256:40b254d736660c604b2e0d89511f156bdecffa634874687f59abb03d95a575ed",
            19503,
        ),
        LTSImage(
            "23.8",
            "clickhouse/clickhouse-server",
            "23.8.16.40",
            "sha256:67307e3248b4acffe032515bb5dd26b8ba447bf9981ad50cbec326d40b1801a6",
            19508,
        ),
        LTSImage(
            "24.3",
            "clickhouse/clickhouse-server",
            "24.3.18.7",
            "sha256:85b97f63dcfff47790d26bb5d5801637aaddb2b93e5e9aee27a686c2fb2b9916",
            19603,
        ),
        LTSImage(
            "24.8",
            "clickhouse/clickhouse-server",
            "24.8.14.39",
            "sha256:1ffa82edee000a42c09313bd9f1293d94c570aee74babc1b3ca9983a35fa597b",
            19608,
        ),
        LTSImage(
            "25.3",
            "clickhouse/clickhouse-server",
            "25.3.14.14",
            "sha256:b627d7a9bc0e0c1bac26cdbe9d2fc6316faa29c5d8a174f28f5abd57d0fa6ba2",
            19703,
        ),
        LTSImage(
            "25.8",
            "clickhouse/clickhouse-server",
            "25.8.28.1",
            "sha256:a9d328123ff8a61bf6b16448528b577d59deb85758172e13b09054b0727f8adf",
            19708,
        ),
        LTSImage(
            "26.3",
            "clickhouse/clickhouse-server",
            "26.3.17.4",
            "sha256:85c434814ac8905e5648027ce926f74ab067edd6aadbccb6c0c165cd3571ea49",
            19803,
        ),
    )
}

SUPPORTED_MACHINES = frozenset({"amd64", "x86_64"})


def compatible_architecture(machine: str | None = None) -> bool:
    return (machine or platform.machine()).lower() in SUPPORTED_MACHINES


def _run(
    command: list[str],
    *,
    check: bool = True,
    capture_output: bool = False,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        check=check,
        text=True,
        capture_output=capture_output,
        env=env,
    )


def _container_image(name: str) -> str | None:
    result = _run(
        ["docker", "inspect", "--format", "{{.Config.Image}}", name],
        check=False,
        capture_output=True,
    )
    if result.returncode != 0:
        return None
    return result.stdout.strip()


def _container_run_command(image: LTSImage) -> list[str]:
    return [
        "docker",
        "run",
        "--detach",
        "--name",
        image.container_name,
        "--platform",
        "linux/amd64",
        "--ulimit",
        "nofile=262144:262144",
        "--env",
        "CLICKHOUSE_SKIP_USER_SETUP=1",
        "--publish",
        f"127.0.0.1:{image.host_port}:9000",
        image.reference,
    ]


def ensure_container(image: LTSImage) -> None:
    existing_image = _container_image(image.container_name)
    if existing_image is not None:
        if existing_image != image.reference:
            raise RuntimeError(
                f"container {image.container_name} uses {existing_image}, expected "
                f"{image.reference}; remove or rename the stale test container"
            )
        print(f"REUSE {image.container_name} ({image.branch})", flush=True)
        _run(["docker", "start", image.container_name], check=False)
        return

    print(f"START {image.container_name} from {image.reference}", flush=True)
    _run(_container_run_command(image))


def wait_until_ready(image: LTSImage, timeout_seconds: float) -> None:
    deadline = time.monotonic() + timeout_seconds
    command = [
        "docker",
        "exec",
        image.container_name,
        "clickhouse-client",
        "--query",
        "SELECT 1",
    ]
    while time.monotonic() < deadline:
        result = _run(command, check=False, capture_output=True)
        if result.returncode == 0 and result.stdout.strip() == "1":
            print(f"READY {image.container_name}", flush=True)
            return
        time.sleep(2.0)
    _run(["docker", "logs", image.container_name], check=False)
    raise RuntimeError(f"ClickHouse LTS {image.branch} did not become ready")


def run_compatibility_tests(image: LTSImage, repository_root: Path) -> None:
    environment = os.environ.copy()
    environment.update(
        {
            "CH_DIAG_TEST_HOST": "127.0.0.1",
            "CH_DIAG_TEST_PORT": str(image.host_port),
        }
    )
    environment.pop("CH_DIAG_TEST_CLUSTER", None)
    _run(
        [
            sys.executable,
            "-m",
            "pytest",
            "-q",
            "tests/integration/test_live_clickhouse.py::"
            "test_every_applicable_node_sql_executes_without_runtime_error",
        ],
        env=environment,
    )

    report_dir = repository_root / ".test_state" / "lts" / image.branch
    _run(
        [
            sys.executable,
            "-m",
            "ch_diag.cli",
            "one-shot",
            "--host",
            "127.0.0.1",
            "--port",
            str(image.host_port),
            "--collection-mode",
            "remote-db-only",
            "--target-scope",
            "node",
            "--item-id",
            "overview.server",
            "--output-format",
            "json",
            "--out-dir",
            str(report_dir),
        ]
    )


def remove_container(image: LTSImage) -> None:
    _run(["docker", "rm", "--force", image.container_name], check=False)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--branch",
        action="append",
        choices=sorted(LTS_IMAGES),
        help="LTS branch to test; repeat as needed; defaults to the full matrix",
    )
    parser.add_argument(
        "--remove",
        action="store_true",
        help="remove containers after the run; local runs retain and reuse them by default",
    )
    parser.add_argument("--startup-timeout", type=float, default=120.0)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if not compatible_architecture():
        print(
            "SKIP ClickHouse LTS matrix: the oldest official images are linux/amd64 "
            f"but runner architecture is {platform.machine()}",
            flush=True,
        )
        return 0
    if shutil.which("docker") is None:
        print("ERROR docker executable is required", file=sys.stderr)
        return 2

    root = Path(__file__).resolve().parents[1]
    selected = args.branch or list(LTS_IMAGES)
    failed = False
    for branch in selected:
        image = LTS_IMAGES[branch]
        try:
            ensure_container(image)
            wait_until_ready(image, args.startup_timeout)
            run_compatibility_tests(image, root)
            print(f"PASS ClickHouse LTS {branch}", flush=True)
        except (RuntimeError, subprocess.CalledProcessError) as exc:
            failed = True
            print(f"FAIL ClickHouse LTS {branch}: {exc}", file=sys.stderr, flush=True)
            _run(["docker", "logs", image.container_name], check=False)
        finally:
            if args.remove:
                remove_container(image)
        if failed:
            break
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
