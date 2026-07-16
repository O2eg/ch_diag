"""Load composable host scripts and inject bounded runtime context."""

from __future__ import annotations

from pathlib import Path
import shlex
from typing import Any


def load_host_script(content_path: Path, manifest: dict[str, Any]) -> str:
    root = content_path / "scripts"
    pieces: list[str] = []
    library = manifest.get("library")
    if library:
        pieces.append((root / str(library)).read_text(encoding="utf-8"))
    pieces.append((root / str(manifest["file"])).read_text(encoding="utf-8"))
    return "\n".join(piece.rstrip() for piece in pieces) + "\n"


def render_host_script(source: str, runtime_context: dict[str, Any]) -> str:
    values = {
        "CH_DIAG_DATABASE_HOST": runtime_context.get("database_host_ip") or "",
        "CH_DIAG_DATABASE_PORT": runtime_context.get("database_port") or "",
    }
    assignments = [
        f"{name}={shlex.quote(str(value))}"
        for name, value in values.items()
    ]
    assignments.append("export CH_DIAG_DATABASE_HOST CH_DIAG_DATABASE_PORT")
    return "\n".join(assignments) + "\n" + source
