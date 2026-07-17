"""Command-line interface for reusable report review runs."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path
import sys

from .config import DEFAULT_CONFIG, load_review_config
from .fixture import FixtureError, ReviewFixture
from .matrix import MatrixRunner, build_cases
from .workload import ReviewWorkload


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default=str(DEFAULT_CONFIG), help="review TOML configuration")
    parser.add_argument("--output-root", help="override configured report root")
    parser.add_argument("--run-id", help="output subdirectory; defaults to a UTC timestamp")
    parser.add_argument(
        "--external-fixture",
        action="store_true",
        help="use configured endpoints without starting, seeding or stopping Compose",
    )
    parser.add_argument("--skip-browser", action="store_true", help="skip headless HTML loading")
    parser.add_argument("--strict", action="store_true", help="fail on any non-zero ch-diag exit")
    parser.add_argument("--list-cases", action="store_true", help="print the configured matrix and exit")
    return parser.parse_args(argv)


def _with_overrides(config, args: argparse.Namespace):
    from dataclasses import replace

    fixture = replace(config.fixture, manage=False) if args.external_fixture else config.fixture
    matrix = config.matrix
    if args.output_root:
        output_root = Path(args.output_root).expanduser()
        if not output_root.is_absolute():
            output_root = Path.cwd() / output_root
        matrix = replace(matrix, output_root=output_root.resolve())
    if args.strict:
        matrix = replace(matrix, strict_collection=True)
    runtime = (
        replace(config.runtime, browser_validation=False) if args.skip_browser else config.runtime
    )
    return replace(config, fixture=fixture, matrix=matrix, runtime=runtime)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        config = _with_overrides(load_review_config(args.config), args)
    except (OSError, TypeError, ValueError) as exc:
        print(f"ERROR invalid review configuration: {exc}", file=sys.stderr)
        return 2
    if args.list_cases:
        for case in build_cases(config):
            print(case.case_id)
        return 0

    run_id = args.run_id or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    if Path(run_id).name != run_id or run_id in {"", ".", ".."}:
        print("ERROR --run-id must be a single safe path component", file=sys.stderr)
        return 2
    destination = config.matrix.output_root / run_id
    fixture = ReviewFixture(config)
    try:
        fixture.prepare()
        workload = ReviewWorkload(config)
        workload.prepare()
        _summary, failed = MatrixRunner(
            config,
            output_directory=destination,
            workload=workload,
        ).run()
    except (FixtureError, FileNotFoundError, OSError, RuntimeError) as exc:
        print(f"FAIL report review matrix: {exc}", file=sys.stderr)
        fixture.show_logs()
        return 1
    finally:
        fixture.close()
    print(f"REPORT INDEX {destination / 'index.html'}", flush=True)
    print(f"REPORT SUMMARY {destination / 'review-summary.json'}", flush=True)
    return 1 if failed else 0
