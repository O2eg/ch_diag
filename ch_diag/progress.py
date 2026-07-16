"""Progress output duplicated to the terminal and an optional log file."""

from __future__ import annotations

from datetime import datetime, timezone
import os
from pathlib import Path
from typing import TextIO


class ProgressReporter:
    def __init__(self, total: int = 0, *, log_path: str | Path | None = None) -> None:
        self.total = max(0, int(total))
        self.completed = 0
        self._log: TextIO | None = None
        if log_path is not None:
            path = Path(os.path.abspath(Path(log_path).expanduser()))
            path.parent.mkdir(parents=True, exist_ok=True)
            flags = os.O_WRONLY | os.O_CREAT | os.O_APPEND | getattr(os, "O_CLOEXEC", 0)
            flags |= getattr(os, "O_NOFOLLOW", 0)
            descriptor = os.open(path, flags, 0o600)
            os.fchmod(descriptor, 0o600)
            self._log = os.fdopen(descriptor, "a", encoding="utf-8")

    def configure(self, total: int) -> None:
        self.total = max(0, int(total))

    def info(self, message: str) -> None:
        self._emit(message)

    def item(self, item_id: str, status: str, reason: str | None = None) -> None:
        self.completed += 1
        percent = 100.0 if self.total <= 0 else min(100.0, self.completed * 100.0 / self.total)
        printable_reason = (
            "".join(character for character in str(reason) if character >= " ")
            if reason
            else ""
        )
        normalized_reason = " ".join(printable_reason.split())[:1000]
        suffix = f" reason={normalized_reason}" if normalized_reason else ""
        self._emit(f"PROGRESS {percent:6.2f}% item={item_id} status={status}{suffix}")

    def close(self) -> None:
        if self._log is not None:
            self._log.close()
            self._log = None

    def _emit(self, message: str) -> None:
        line = f"{datetime.now(timezone.utc).isoformat()} {message}"
        print(line, flush=True)
        if self._log is not None:
            self._log.write(line + "\n")
            self._log.flush()
