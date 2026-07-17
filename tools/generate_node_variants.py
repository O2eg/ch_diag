#!/usr/bin/env python3
"""Generate explicit standalone-node SQL variants from diagnostic cluster queries.

The runtime never rewrites a cluster query into a node query.  This maintainer
tool creates reviewable SQL files and manifest variants instead.  Cluster-only
diagnostics which compare hosts are deliberately excluded.
"""

from __future__ import annotations

import argparse
from copy import deepcopy
from pathlib import Path
import re
from typing import Any

import yaml


CLUSTER_ONLY_QUERY_IDS = {
    "diagnostics.db.db_asymmetric_tbls",
    "diagnostics.db.db_distr_by_hosts",
    "diagnostics.db.db_distr_engines_by_hosts",
    "diagnostics.db.db_distr_tbl_engines",
    "diagnostics.db.db_distr_tbl_engines_by_hosts",
    "diagnostics.db.db_symmetric_tbls",
    "diagnostics.db.db_tbls_with_diff_ddls",
    "diagnostics.queries.queries_by_hosts_common",
}

_CLUSTER_TABLE = re.compile(
    r"clusterAllReplicas\s*\(\s*\{\{cluster\}\}\s*,\s*(system\.[A-Za-z_][A-Za-z0-9_]*)\s*\)",
    flags=re.IGNORECASE,
)


def node_sql(cluster_sql: str, source: str) -> str:
    """Replace cluster table functions with local, identity-preserving sources."""

    def replace(match: re.Match[str]) -> str:
        table = match.group(1)
        return f"(SELECT 1 AS _shard_num, 1 AS _replica_num, * FROM {table})"

    rendered, replacements = _CLUSTER_TABLE.subn(replace, cluster_sql)
    if "{{cluster}}" in rendered:
        raise ValueError(f"unsupported cluster placeholder in {source}")
    if "clusterAllReplicas" in cluster_sql and replacements == 0:
        raise ValueError(f"cannot convert clusterAllReplicas call in {source}")
    return (
        "-- Generated standalone-node variant. Do not edit directly; "
        "see tools/generate_node_variants.py.\n" + rendered
    )


def generate(repo: Path) -> tuple[int, int]:
    content = repo / "ch_diag" / "content"
    catalog_path = content / "queries.yaml"
    catalog = yaml.safe_load(catalog_path.read_text(encoding="utf-8"))
    query_root = content / str(catalog["query_catalog"].get("sql_root", "queries"))
    generated_files = 0
    generated_variants = 0

    for query_id, query in catalog["queries"].items():
        if not query_id.startswith("diagnostics.") or query_id in CLUSTER_ONLY_QUERY_IDS:
            continue
        cluster_variants = [
            variant
            for variant in query.get("variants", [])
            if "cluster" in set(variant.get("scopes") or [])
            and "node" not in set(variant.get("scopes") or [])
        ]
        existing_node_ids = {
            str(variant.get("derived_from"))
            for variant in query.get("variants", [])
            if "node" in set(variant.get("scopes") or []) and variant.get("derived_from")
        }
        additions: list[dict[str, Any]] = []
        for cluster_variant in cluster_variants:
            cluster_id = str(cluster_variant["id"])
            source_relative = Path(str(cluster_variant["sql_file"]))
            source_path = query_root / source_relative
            node_relative = Path("node") / source_relative.relative_to("cluster")
            node_path = query_root / node_relative
            node_path.parent.mkdir(parents=True, exist_ok=True)
            node_path.write_text(
                node_sql(source_path.read_text(encoding="utf-8"), source_relative.as_posix()),
                encoding="utf-8",
            )
            generated_files += 1

            if cluster_id in existing_node_ids:
                continue

            node_variant = deepcopy(cluster_variant)
            node_variant["id"] = cluster_id + "_node"
            node_variant["scopes"] = ["node"]
            node_variant["sql_file"] = node_relative.as_posix()
            node_variant["derived_from"] = cluster_id
            additions.append(node_variant)
            generated_variants += 1
        query.setdefault("variants", []).extend(additions)

    catalog_path.write_text(
        yaml.safe_dump(catalog, sort_keys=False, allow_unicode=True, width=100),
        encoding="utf-8",
    )
    return generated_files, generated_variants


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("repo", nargs="?", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    files, variants = generate(args.repo.resolve())
    print(f"generated node SQL files: {files}; manifest variants: {variants}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
