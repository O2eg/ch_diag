"""Build, execute and validate the complete human-review report matrix."""

from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from html import escape
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
from typing import Any

from ch_diag.artifact import validate_artifact
from ch_diag.errors import ChDiagError

from .config import ROOT, ReviewConfig
from .workload import ReviewWorkload


@dataclass(frozen=True)
class ReportCase:
    mode: str
    scope: str
    run_type: str

    @property
    def case_id(self) -> str:
        return f"{self.mode}/{self.scope}/{self.run_type}"


def build_cases(config: ReviewConfig) -> tuple[ReportCase, ...]:
    return tuple(
        ReportCase(mode=mode, scope=scope, run_type=run_type)
        for mode in config.matrix.modes
        for scope in config.matrix.scopes
        for run_type in config.matrix.run_types
    )


def build_command(config: ReviewConfig, case: ReportCase, output_directory: Path) -> list[str]:
    database = config.database
    command = [
        str(config.runtime.ch_diag_executable),
        case.run_type,
        "--host",
        database.host,
        "--port",
        str(database.port),
        "--database",
        database.database,
        "--user",
        database.user,
        "--password-env",
        database.password_env,
        "--collection-mode",
        case.mode,
        "--target-scope",
        case.scope,
        "--out-dir",
        str(output_directory),
        "--output-format",
        ",".join(config.matrix.formats),
        "--log-file",
        str(output_directory / "run.log"),
    ]
    if case.scope == "cluster":
        command.extend(["--cluster-name", database.cluster_name])
    if case.mode == "remote":
        ssh = config.ssh
        command.extend(
            [
                "--ssh-host",
                ssh.host,
                "--ssh-port",
                str(ssh.port),
                "--ssh-user",
                ssh.user,
                "--ssh-key",
                str(ssh.key),
                "--ssh-known-hosts",
                str(ssh.known_hosts),
            ]
        )
    if case.run_type == "snapshots":
        for tag in config.matrix.snapshot_tags:
            command.extend(["--tags", tag])
        command.extend(
            [
                "--duration",
                str(config.matrix.snapshot_duration_seconds),
                "--interval",
                str(config.matrix.snapshot_interval_seconds),
            ]
        )
    return command


def _find_single(directory: Path, suffix: str) -> Path:
    matches = sorted(directory.glob(f"*{suffix}"))
    if len(matches) != 1:
        raise ValueError(
            f"expected exactly one {suffix} report in {directory}, found {len(matches)}"
        )
    return matches[0]


def _browser_executable(config: ReviewConfig) -> str | None:
    configured = config.runtime.browser_executable
    if configured:
        return shutil.which(configured) or (
            configured if Path(configured).is_file() else None
        )
    for candidate in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser"):
        resolved = shutil.which(candidate)
        if resolved:
            return resolved
    return None


def validate_in_browser(config: ReviewConfig, html_path: Path) -> dict[str, Any]:
    if not config.runtime.browser_validation:
        return {"status": "skipped", "reason": "disabled by configuration"}
    executable = _browser_executable(config)
    if executable is None:
        return {"status": "skipped", "reason": "Chrome/Chromium was not found"}
    config.fixture.state_directory.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(
        prefix="chrome-", dir=config.fixture.state_directory
    ) as profile:
        try:
            result = subprocess.run(
                [
                    executable,
                    "--headless=new",
                    "--disable-gpu",
                    "--no-first-run",
                    "--disable-background-networking",
                    "--disable-component-update",
                    f"--user-data-dir={profile}",
                    "--virtual-time-budget=1500",
                    "--dump-dom",
                    html_path.resolve().as_uri(),
                ],
                cwd=ROOT,
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                text=True,
                timeout=config.runtime.browser_timeout_seconds,
            )
        except subprocess.TimeoutExpired:
            return {"status": "error", "reason": "headless browser timed out"}
    if result.returncode != 0:
        message = result.stderr.strip()[-1000:] or f"browser exited {result.returncode}"
        return {"status": "error", "reason": message}
    return {"status": "ok", "executable": executable}


def validate_report(config: ReviewConfig, directory: Path) -> dict[str, Any]:
    json_path = _find_single(directory, ".json")
    html_path = _find_single(directory, ".html")
    artifact = json.loads(json_path.read_text(encoding="utf-8"))
    validate_artifact(artifact)
    rendered = html_path.read_text(encoding="utf-8")
    required_markers = (
        "<!doctype html>",
        '<script id="ch-diag-artifact" type="application/json">',
        'artifact_schema_version',
    )
    missing = [marker for marker in required_markers if marker not in rendered]
    if missing:
        raise ValueError(f"HTML report misses marker(s): {missing!r}")
    statuses = Counter(
        str(item.get("collection_status")) for item in artifact["items"].values()
    )
    diagnostics = Counter(
        str(item.get("code") or "unknown") for item in artifact.get("diagnostics", [])
    )
    charts_without_data = sorted(
        item_id
        for item_id, item in artifact["items"].items()
        if (item.get("result") or {}).get("kind") == "chart"
        and not (item.get("result") or {}).get("series_count")
    )
    browser = validate_in_browser(config, html_path)
    return {
        "json": str(json_path.resolve()),
        "html": str(html_path.resolve()),
        "json_bytes": json_path.stat().st_size,
        "html_bytes": html_path.stat().st_size,
        "item_count": len(artifact["items"]),
        "snapshot_count": len(artifact["snapshots"]),
        "collection_statuses": dict(sorted(statuses.items())),
        "diagnostic_codes": dict(sorted(diagnostics.items())),
        "charts_without_data": charts_without_data,
        "browser": browser,
    }


def _index_html(summary: dict[str, Any], destination: Path) -> str:
    rows: list[str] = []
    for result in summary["cases"]:
        case = result["case"]
        validation = result.get("validation") or {}
        html_path = validation.get("html")
        if html_path:
            link = escape(str(Path(html_path).relative_to(destination)))
            report = f'<a href="{link}">open HTML</a>'
        else:
            report = "not generated"
        statuses = escape(json.dumps(validation.get("collection_statuses", {}), sort_keys=True))
        browser = escape(str((validation.get("browser") or {}).get("status", "-")))
        error = escape(str(result.get("error") or ""))
        rows.append(
            "<tr>"
            f"<td><code>{escape(case['mode'])}</code></td>"
            f"<td>{escape(case['scope'])}</td>"
            f"<td>{escape(case['run_type'])}</td>"
            f"<td>{result['collection_exit_code']}</td>"
            f"<td>{statuses}</td>"
            f"<td>{browser}</td>"
            f"<td>{report}</td>"
            f"<td>{error}</td>"
            "</tr>"
        )
    return """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>ch_diag review matrix</title>
<style>
body{font:14px system-ui,sans-serif;margin:2rem;color:#20242a;background:#f6f7f9}
table{border-collapse:collapse;width:100%%;background:white}th,td{border:1px solid #d8dce2;padding:.55rem;text-align:left;vertical-align:top}
th{background:#eceff3}code{white-space:nowrap}a{color:#0757b9}h1{margin-bottom:.3rem}.meta{color:#5b6470;margin-bottom:1.5rem}
</style></head><body>
<h1>ch_diag report review matrix</h1>
<div class="meta">Generated: %s · Cases: %d</div>
<table><thead><tr><th>Mode</th><th>Scope</th><th>Run</th><th>Exit</th><th>Statuses</th><th>Browser</th><th>Report</th><th>Error</th></tr></thead>
<tbody>%s</tbody></table></body></html>
""" % (escape(summary["generated_at"]), len(summary["cases"]), "".join(rows))


class MatrixRunner:
    def __init__(
        self,
        config: ReviewConfig,
        *,
        output_directory: Path,
        workload: ReviewWorkload | None = None,
    ) -> None:
        self.config = config
        self.output_directory = output_directory.resolve()
        self.workload = workload or ReviewWorkload(config)

    def run(self) -> tuple[dict[str, Any], bool]:
        executable = self.config.runtime.ch_diag_executable
        if not executable.is_file():
            raise FileNotFoundError(f"ch-diag executable does not exist: {executable}")
        self.output_directory.mkdir(parents=True, exist_ok=True)
        results: list[dict[str, Any]] = []
        failed = False
        for case in build_cases(self.config):
            case_directory = self.output_directory / case.mode / case.scope / case.run_type
            case_directory.mkdir(parents=True, exist_ok=True)
            command = build_command(self.config, case, case_directory)
            print(f"RUN {case.case_id}", flush=True)
            with self.workload.running(
                enabled=case.run_type == "snapshots",
                log_path=case_directory / "workload.log",
            ) as workload_summary:
                completed = subprocess.run(command, cwd=ROOT, check=False)
            entry: dict[str, Any] = {
                "case": asdict(case),
                "collection_exit_code": completed.returncode,
                "command": command,
                "workload": workload_summary,
            }
            try:
                entry["validation"] = validate_report(self.config, case_directory)
                browser_status = entry["validation"]["browser"]["status"]
                if browser_status == "error":
                    failed = True
                if (
                    case.run_type == "snapshots"
                    and self.config.workload.enabled
                    and entry["validation"]["charts_without_data"]
                ):
                    entry["error"] = (
                        "snapshot charts without data: "
                        + ", ".join(entry["validation"]["charts_without_data"])
                    )
                    failed = True
            except (ChDiagError, OSError, ValueError, json.JSONDecodeError) as exc:
                entry["error"] = str(exc)
                failed = True
            if completed.returncode != 0 and self.config.matrix.strict_collection:
                failed = True
            if (
                case.run_type == "snapshots"
                and self.config.workload.enabled
                and not workload_summary.get("successful_cycles")
            ):
                entry["error"] = entry.get("error") or "review workload completed no cycles"
                failed = True
            results.append(entry)
            print(
                f"DONE {case.case_id} exit={completed.returncode} "
                f"validated={'validation' in entry}",
                flush=True,
            )

        summary = {
            "schema_version": 1,
            "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "configuration": str(self.config.source),
            "output_directory": str(self.output_directory),
            "strict_collection": self.config.matrix.strict_collection,
            "cases": results,
        }
        summary_path = self.output_directory / "review-summary.json"
        summary_path.write_text(
            json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        index_path = self.output_directory / "index.html"
        index_path.write_text(_index_html(summary, self.output_directory), encoding="utf-8")
        summary_path.chmod(0o600)
        index_path.chmod(0o600)
        return summary, failed
