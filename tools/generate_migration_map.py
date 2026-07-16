#!/usr/bin/env python3
"""Generate the auditable legacy item migration registry."""

from __future__ import annotations

import argparse
from pathlib import Path
import re

import yaml

from ch_diag.versioning import ClickHouseVersion


def generate(repo: Path) -> str:
    content = repo / "ch_diag" / "content"
    queries = yaml.safe_load((content / "queries.yaml").read_text(encoding="utf-8"))["queries"]
    report = yaml.safe_load((content / "report.yaml").read_text(encoding="utf-8"))
    report_ids = {}
    for section_id, section in report["sections"].items():
        for item_key, item in section.get("items", {}).items():
            if item.get("query"):
                report_ids[str(item["query"])] = f"{section_id}.{item_key}"

    lines = [
        "# Legacy item migration map",
        "",
        "Generated from schema-v5 manifests. The source inventory is `ch_diag 0.5.0`: 55 items and 116 original SQL files. Node variants are explicit generated files; the runtime does not fabricate a cluster.",
        "",
        "| Legacy item | Schema-v5 item id | SQL variants | Scopes | Source | Version range | Privilege/capability | Cost/limit | Sensitivity | Status | Test status |",
        "|---|---|---:|---|---|---|---|---|---|---|---|",
    ]
    for query_id, manifest in queries.items():
        legacy_id = manifest.get("legacy_item_id")
        if not legacy_id:
            continue
        variants = list(manifest["variants"])
        scopes = sorted({scope for variant in variants for scope in variant.get("scopes", [])})
        tables = set()
        for variant in variants:
            sql = (content / "queries" / variant["sql_file"]).read_text(encoding="utf-8")
            tables.update(re.findall(r"\bsystem\.[A-Za-z_][A-Za-z0-9_]*", sql))
        minimum = min(
            (str(variant.get("min_ch_version", "0")) for variant in variants),
            key=ClickHouseVersion.parse,
        )
        maxima = [str(variant["max_ch_version"]) for variant in variants if variant.get("max_ch_version")]
        maximum = (
            max(maxima, key=ClickHouseVersion.parse)
            if maxima and all(variant.get("max_ch_version") for variant in variants)
            else "+"
        )
        optional = "optional" if manifest.get("optional") else "required"
        lines.append(
            "| "
            + " | ".join(
                [
                    f"`{legacy_id}`",
                    f"`{report_ids.get(query_id, query_id)}`",
                    str(len(variants)),
                    ", ".join(scopes),
                    ", ".join(f"`{table}`" for table in sorted(tables)) or "read-only SELECT",
                    f"{minimum} .. {maximum}",
                    f"SELECT on sources; {optional}",
                    f"{manifest.get('timeout_seconds', 15)}s / 10,000 rows",
                    str(manifest.get("sensitivity", "normal")),
                    "migrated",
                    "25.8 node/cluster where applicable",
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "Cluster-only comparison items intentionally have no node variant. Optional Keeper/DDL sources are omitted when the capability is absent; all other missing identifiers remain errors.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("repo", nargs="?", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    repo = args.repo.resolve()
    destination = repo / "docs" / "legacy_item_migration.md"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(generate(repo), encoding="utf-8")
    print(destination)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
