#!/usr/bin/env python3
"""Run the real legacy ClickHouse SQL compatibility matrix.

The public legacy images are linux/amd64 only.  On another architecture the
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
class LegacyImage:
    boundary: str
    repository: str
    version: str
    digest: str
    host_port: int

    @property
    def reference(self) -> str:
        return f"{self.repository}:{self.version}@{self.digest}"

    @property
    def container_name(self) -> str:
        return "chdiag-legacy-" + self.boundary.replace(".", "-")


LEGACY_IMAGES: dict[str, LegacyImage] = {
    item.boundary: item
    for item in (
        LegacyImage(
            "20.3",
            "yandex/clickhouse-server",
            "20.3.21.2",
            "sha256:e9c704ac6dc7f11e09b3c00d784625ac6f7c4fe9c9050c1d4b61b572f2bdd434",
            19203,
        ),
        LegacyImage(
            "20.11",
            "yandex/clickhouse-server",
            "20.11.6.6",
            "sha256:d728866bd5527c0295dda3f81387f2aa859704a069484395bc9bd3c382e167fa",
            19211,
        ),
        LegacyImage(
            "21.1",
            "yandex/clickhouse-server",
            "21.1.9.41",
            "sha256:4d9d04a76931b5d8fc123006b7e1f89fd73275879fdc4aaa13009aafdc3fddde",
            19301,
        ),
        LegacyImage(
            "21.4",
            "yandex/clickhouse-server",
            "21.4.7.3",
            "sha256:399f58d0c7680903c56ef3c536334b26b057cb166e169165d52307a4a765035c",
            19304,
        ),
        LegacyImage(
            "21.8",
            "clickhouse/clickhouse-server",
            "21.8.15.7",
            "sha256:a9141f199e4b1f60cd6fe5ee58e25a86938117d26a73c4a1fa5c31b6e2f64abf",
            19308,
        ),
        LegacyImage(
            "21.11",
            "clickhouse/clickhouse-server",
            "21.11.11.1",
            "sha256:a3c17fb19954ceb084d6227a7270ab2255570da5e47e64640586762496403d09",
            19311,
        ),
        LegacyImage(
            "22.2",
            "clickhouse/clickhouse-server",
            "22.2.3.5",
            "sha256:3eb11dccb5cae84da3edb1b97075e037f70265b0c13273d01622f3f2a088ce96",
            19402,
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


def ensure_container(image: LegacyImage) -> None:
    existing_image = _container_image(image.container_name)
    if existing_image is not None:
        if existing_image != image.reference:
            raise RuntimeError(
                f"container {image.container_name} uses {existing_image}, expected "
                f"{image.reference}; remove or rename the stale test container"
            )
        print(f"REUSE {image.container_name} ({image.boundary})", flush=True)
        _run(["docker", "start", image.container_name], check=False)
        return

    print(f"START {image.container_name} from {image.reference}", flush=True)
    _run(
        [
            "docker",
            "run",
            "--detach",
            "--name",
            image.container_name,
            "--platform",
            "linux/amd64",
            "--ulimit",
            "nofile=262144:262144",
            "--publish",
            f"127.0.0.1:{image.host_port}:9000",
            image.reference,
        ]
    )


def wait_until_ready(image: LegacyImage, timeout_seconds: float) -> None:
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
    raise RuntimeError(f"ClickHouse {image.boundary} did not become ready")


def run_compatibility_tests(image: LegacyImage, repository_root: Path) -> None:
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

    report_dir = repository_root / ".test_state" / "legacy" / image.boundary
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


def remove_container(image: LegacyImage) -> None:
    _run(["docker", "rm", "--force", image.container_name], check=False)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--boundary",
        action="append",
        choices=sorted(LEGACY_IMAGES),
        help="boundary to test; repeat as needed; defaults to the full matrix",
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
            "SKIP legacy ClickHouse matrix: official boundary images are linux/amd64 "
            f"but runner architecture is {platform.machine()}",
            flush=True,
        )
        return 0
    if shutil.which("docker") is None:
        print("ERROR docker executable is required", file=sys.stderr)
        return 2

    root = Path(__file__).resolve().parents[1]
    selected = args.boundary or list(LEGACY_IMAGES)
    failed = False
    for boundary in selected:
        image = LEGACY_IMAGES[boundary]
        try:
            ensure_container(image)
            wait_until_ready(image, args.startup_timeout)
            run_compatibility_tests(image, root)
            print(f"PASS ClickHouse {boundary}", flush=True)
        except (RuntimeError, subprocess.CalledProcessError) as exc:
            failed = True
            print(f"FAIL ClickHouse {boundary}: {exc}", file=sys.stderr, flush=True)
            _run(["docker", "logs", image.container_name], check=False)
        finally:
            if args.remove:
                remove_container(image)
        if failed:
            break
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
