"""Compatibility wrapper for the flat ch_diag 0.5 command line."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
from typing import Sequence

from . import __version__
from .cli import main as modern_main


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ch_diag.py",
        description="Compatibility wrapper; new automation should use ch-diag",
    )
    parser.add_argument("--version", action="store_true")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=9000)
    parser.add_argument("--database", default="default")
    parser.add_argument("--user", default="default")
    parser.add_argument("--password")
    parser.add_argument("--cluster-name", default="AUTO")
    parser.add_argument("--certfile", default="")
    parser.add_argument("--keyfile", default="")
    parser.add_argument("--ca-certs", default="")
    parser.add_argument("--debug", action="store_true")
    parser.add_argument("--add-params-to-report", action="store_true")
    parser.add_argument("--use-ts-in-output-file-name", action="store_true")
    parser.add_argument("--out-dir", default="output")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.version:
        print(__version__)
        return 0
    print(
        "ch_diag.py: warning: legacy CLI translated to the schema-v5 collector; "
        "migrate automation to ch-diag one-shot",
        file=sys.stderr,
    )
    modern = [
        "one-shot",
        "--host",
        args.host,
        "--port",
        str(args.port),
        "--database",
        args.database,
        "--user",
        args.user,
        "--collection-mode",
        "remote-db-only",
        "--target-scope",
        "cluster",
        "--cluster-name",
        args.cluster_name,
        "--output-format",
        "html",
        "--out-dir",
        str(Path(args.out_dir)),
    ]
    if args.password is not None:
        modern.extend(("--password", args.password))
    for option, value in (
        ("--certfile", args.certfile),
        ("--keyfile", args.keyfile),
        ("--ca-certs", args.ca_certs),
    ):
        if value:
            modern.extend((option, value))
    return modern_main(modern)
