#!/usr/bin/env python3
"""Fail when a release tag does not equal the package version."""

from __future__ import annotations

import argparse
import os
from pathlib import Path


def project_version(path: Path) -> str:
    try:
        import tomllib
    except ModuleNotFoundError:  # pragma: no cover - Python 3.10 only
        import tomli as tomllib  # type: ignore[no-redef]
    with path.open("rb") as stream:
        return str(tomllib.load(stream)["project"]["version"])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("tag", nargs="?", default=os.environ.get("GITHUB_REF_NAME"))
    args = parser.parse_args()
    if not args.tag:
        parser.error("release tag is required")
    tag_version = str(args.tag).removeprefix("v")
    version = project_version(Path("pyproject.toml"))
    if tag_version != version:
        parser.error(f"tag {args.tag!r} does not match project version {version!r}")
    print(f"release version ok: {version}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
