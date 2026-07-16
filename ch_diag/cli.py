"""Command-line interface for the autonomous ch_diag runtime."""

from __future__ import annotations

import argparse
import asyncio
import getpass
import json
import os
from pathlib import Path
import sys
from typing import Any, Sequence

from . import __version__
from .artifact import write_text_secure
from .clickhouse import ConnectionConfig, create_clickhouse_adapter
from .collector import collect_one_shot, collect_snapshots
from .config import resolve_cli_defaults
from .content_loader import (
    build_integrity_manifest,
    default_content_path,
    iter_report_items,
    load_content,
)
from .errors import ChDiagError
from .planner import available_tags, build_plan
from .progress import ProgressReporter
from .render.html import render_from_json
from .runtime_config import (
    COLLECTION_MODES,
    LOCAL_COLLECTION_MODE,
    NODE_SCOPE,
    TARGET_SCOPES,
)
from .ssh_transport import SshConfig
from .versioning import ClickHouseVersion


class _OverrideAppendAction(argparse.Action):
    """Append repeated CLI values, replacing a config/environment default."""

    def __call__(
        self,
        parser: argparse.ArgumentParser,
        namespace: argparse.Namespace,
        values: str,
        option_string: str | None = None,
    ) -> None:
        marker = f"_ch_diag_cli_seen_{self.dest}"
        current = list(getattr(namespace, self.dest, None) or [])
        if not getattr(namespace, marker, False):
            current = []
            setattr(namespace, marker, True)
        current.append(values)
        setattr(namespace, self.dest, current)


def _parser(defaults: dict[str, Any] | None = None) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ch-diag", description="ClickHouse diagnostics")
    parser.add_argument("--config", help="TOML configuration file (must precede command)")
    parser.add_argument("--version", action="version", version=__version__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate = subparsers.add_parser("validate", help="verify and validate a content pack")
    _add_content_argument(validate)

    list_items = subparsers.add_parser("item-id-list", help="list report item ids")
    _add_content_argument(list_items)
    tags_list = subparsers.add_parser("tags-list", help="list report tags")
    _add_content_argument(tags_list)

    explain = subparsers.add_parser("explain-plan", help="show a resolved execution plan")
    _add_content_argument(explain)
    explain.add_argument("--ch-version", required=True)
    _add_selection_arguments(explain)
    explain.add_argument("--run-mode", choices=("one-shot", "snapshots"), default="one-shot")
    explain.add_argument("--collection-mode", choices=sorted(COLLECTION_MODES), default=LOCAL_COLLECTION_MODE)
    explain.add_argument("--target-scope", choices=sorted(TARGET_SCOPES), default=NODE_SCOPE)

    one_shot = subparsers.add_parser("one-shot", help="collect a point-in-time report")
    _add_collection_arguments(one_shot)

    snapshots = subparsers.add_parser("snapshots", help="collect a repeated-sampling report")
    _add_collection_arguments(snapshots)
    snapshots.add_argument("--duration", type=float, default=10.0, help="sampling window in seconds")
    snapshots.add_argument("--interval", type=float, default=5.0, help="sampling interval in seconds")

    render = subparsers.add_parser("render", help="render HTML from a ch_diag JSON artifact")
    render.add_argument("--from-json", required=True)
    render.add_argument("--out", required=True)
    render.add_argument("--strip-meta", action="store_true")

    refresh = subparsers.add_parser("_refresh-content-integrity", help=argparse.SUPPRESS)
    _add_content_argument(refresh)
    if defaults:
        for subparser in subparsers.choices.values():
            supported = {
                action.dest
                for action in subparser._actions
                if action.dest is not argparse.SUPPRESS
            }
            subparser.set_defaults(
                **{key: value for key, value in defaults.items() if key in supported}
            )
    return parser


def _config_path(argv: Sequence[str]) -> str | None:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--config")
    args, _unknown = parser.parse_known_args(argv)
    return args.config


def _add_content_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--content", default=str(default_content_path()))


def _add_selection_arguments(parser: argparse.ArgumentParser) -> None:
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--item-id", action=_OverrideAppendAction, dest="item_ids")
    group.add_argument("--tags", action=_OverrideAppendAction)


def _add_collection_arguments(parser: argparse.ArgumentParser) -> None:
    _add_content_argument(parser)
    _add_selection_arguments(parser)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=9000)
    parser.add_argument("--database", default="default")
    parser.add_argument("--user", default="default")
    parser.add_argument("--password")
    parser.add_argument("--password-env", default="CH_DIAG_PASSWORD")
    parser.add_argument("--password-prompt", action="store_true")
    parser.add_argument("--secure", action=argparse.BooleanOptionalAction, default=False)
    verify = parser.add_mutually_exclusive_group()
    verify.add_argument("--no-verify", action="store_true")
    verify.add_argument("--verify", action="store_false", dest="no_verify")
    parser.add_argument("--ca-certs")
    parser.add_argument("--certfile")
    parser.add_argument("--keyfile")
    parser.add_argument("--server-hostname")
    parser.add_argument("--collection-mode", choices=sorted(COLLECTION_MODES), default=LOCAL_COLLECTION_MODE)
    parser.add_argument("--target-scope", choices=sorted(TARGET_SCOPES), default=NODE_SCOPE)
    parser.add_argument("--cluster-name")
    parser.add_argument("--out-dir", default="reports")
    parser.add_argument("--json-out")
    parser.add_argument("--html-out")
    parser.add_argument("--output-format", action=_OverrideAppendAction, default=None)
    parser.add_argument("--strip-meta", action=argparse.BooleanOptionalAction, default=False)
    parser.add_argument("--log-file")
    parser.add_argument("--ssh-host")
    parser.add_argument("--ssh-port", type=int, default=22)
    parser.add_argument("--ssh-user")
    parser.add_argument("--ssh-key")
    parser.add_argument("--ssh-known-hosts")


def _output_formats(values: list[str] | None) -> tuple[str, ...]:
    if not values:
        return ("json", "html")
    result: list[str] = []
    for raw in values:
        for part in raw.split(","):
            value = part.strip().lower()
            if value and value not in result:
                result.append(value)
    if not result or any(value not in {"json", "html"} for value in result):
        raise ValueError("--output-format accepts only html and/or json")
    return tuple(result)


def _connection(args: argparse.Namespace) -> ConnectionConfig:
    password = args.password
    if password is not None:
        print(
            "ch-diag: warning: --password can be visible in the process list; "
            "prefer --password-prompt or CH_DIAG_PASSWORD",
            file=sys.stderr,
        )
    if password is None and args.password_env:
        password = os.environ.get(args.password_env)
    if args.password_prompt:
        if password is not None:
            raise ValueError("--password-prompt conflicts with --password/password environment")
        password = getpass.getpass("ClickHouse password: ")
    return ConnectionConfig(
        host=args.host,
        port=args.port,
        database=args.database,
        user=args.user,
        password=password,
        secure=bool(args.secure or args.ca_certs or args.certfile or args.keyfile),
        verify=not args.no_verify,
        ca_certs=args.ca_certs,
        certfile=args.certfile,
        keyfile=args.keyfile,
        server_hostname=args.server_hostname,
    )


def _ssh_config(args: argparse.Namespace) -> SshConfig | None:
    values = (args.ssh_host, args.ssh_user, args.ssh_key, args.ssh_known_hosts)
    if not any(values):
        return None
    if not all(values):
        raise ValueError(
            "SSH requires --ssh-host, --ssh-user, --ssh-key and --ssh-known-hosts"
        )
    return SshConfig(
        host=args.ssh_host,
        port=args.ssh_port,
        username=args.ssh_user,
        client_key=args.ssh_key,
        known_hosts=args.ssh_known_hosts,
    )


async def _run_collection(args: argparse.Namespace) -> int:
    content = load_content(args.content)
    reporter = ProgressReporter(log_path=args.log_file)
    try:
        collector = collect_snapshots if args.command == "snapshots" else collect_one_shot
        extra = (
            {"duration_seconds": args.duration, "interval_seconds": args.interval}
            if args.command == "snapshots"
            else {}
        )
        artifacts = await collector(
            content,
            _connection(args),
            out_dir=args.out_dir,
            collection_mode=args.collection_mode,
            target_scope=args.target_scope,
            cluster_name=args.cluster_name,
            item_ids=args.item_ids,
            tags=args.tags,
            output_formats=_output_formats(args.output_format),
            json_out=args.json_out,
            html_out=args.html_out,
            strip_meta=args.strip_meta,
            ssh_config=_ssh_config(args),
            progress=reporter,
            adapter_factory=create_clickhouse_adapter,
            **extra,
        )
    finally:
        reporter.close()
    statuses = {
        str(item.get("collection_status"))
        for artifact in artifacts
        for item in artifact.get("items", {}).values()
    }
    return 1 if "error" in statuses else 0


def _item_rows(content: Any) -> list[dict[str, Any]]:
    rows = []
    for _section, _key, item_id, item in iter_report_items(content):
        kind = next(key for key in ("query", "script", "metric") if item.get(key))
        source = {"query": content.queries, "script": content.scripts, "metric": content.metrics}[
            kind
        ][item[kind]]
        rows.append(
            {
                "item_id": item_id,
                "tags": item.get("tags") or [],
                "description": source.get("description") or source.get("title") or "",
            }
        )
    return rows


def main(argv: Sequence[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    try:
        config_path = _config_path(arguments)
        args = _parser(resolve_cli_defaults(config_path)).parse_args(arguments)
        if args.command == "_refresh-content-integrity":
            content_path = Path(args.content).resolve()
            write_text_secure(content_path / "integrity.sha256", build_integrity_manifest(content_path))
            return 0
        if args.command == "validate":
            content = load_content(args.content)
            print(f"content ok: {content.report['report']['id']} {content.checksum}")
            return 0
        if args.command == "item-id-list":
            content = load_content(args.content)
            for row in _item_rows(content):
                print(f"{row['item_id']}\t{','.join(row['tags'])}\t{row['description']}")
            return 0
        if args.command == "tags-list":
            content = load_content(args.content)
            for tag in available_tags(content):
                print(tag)
            return 0
        if args.command == "explain-plan":
            content = load_content(args.content)
            plan = build_plan(
                content,
                ClickHouseVersion.parse(args.ch_version),
                mode=args.run_mode,
                collection_mode=args.collection_mode,
                target_scope=args.target_scope,
                item_ids=args.item_ids,
                tags=args.tags,
            )
            payload = {
                "mode": plan.mode,
                "collection_mode": plan.collection_mode,
                "target_scope": plan.target_scope,
                "server_version": str(plan.server_version),
                "items": [item.__dict__ for item in plan.items],
            }
            print(json.dumps(payload, ensure_ascii=False, indent=2))
            return 0
        if args.command == "render":
            render_from_json(args.from_json, args.out, strip_meta=args.strip_meta)
            return 0
        if args.command in {"one-shot", "snapshots"}:
            return asyncio.run(_run_collection(args))
        raise ValueError(f"unknown command {args.command!r}")
    except (ChDiagError, ValueError, OSError) as exc:
        print(f"ch-diag: error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
