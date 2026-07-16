from __future__ import annotations

import os
from pathlib import Path

from ch_diag.artifact import write_text_secure
from ch_diag.progress import ProgressReporter


def test_report_and_log_permissions_are_owner_only(tmp_path: Path) -> None:
    report = tmp_path / "report.json"
    log = tmp_path / "run.log"
    write_text_secure(report, "{}\n")
    progress = ProgressReporter(log_path=log)
    progress.info("test")
    progress.close()
    assert os.stat(report).st_mode & 0o777 == 0o600
    assert os.stat(log).st_mode & 0o777 == 0o600


def test_atomic_output_replaces_symlink_instead_of_following_it(tmp_path: Path) -> None:
    target = tmp_path / "target"
    target.write_text("protected", encoding="utf-8")
    destination = tmp_path / "report"
    destination.symlink_to(target)
    write_text_secure(destination, "report")
    assert target.read_text(encoding="utf-8") == "protected"
    assert not destination.is_symlink()
    assert destination.read_text(encoding="utf-8") == "report"
