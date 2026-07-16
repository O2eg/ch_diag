from __future__ import annotations

from pathlib import Path
import xml.etree.ElementTree as ET

import yaml


ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "tests" / "integration" / "multinode"


def test_multinode_topology_is_one_shard_with_two_distinct_replicas() -> None:
    cluster = ET.parse(FIXTURE / "clickhouse-cluster.xml").getroot()
    shards = cluster.findall("./remote_servers/chdiag_cluster/shard")
    assert len(shards) == 1
    replicas = shards[0].findall("replica")
    assert [replica.findtext("host") for replica in replicas] == ["node1", "node2"]
    assert shards[0].findtext("internal_replication") == "true"

    node1 = ET.parse(FIXTURE / "node1-macros.xml").getroot()
    node2 = ET.parse(FIXTURE / "node2-macros.xml").getroot()
    assert node1.findtext("./macros/shard") == node2.findtext("./macros/shard") == "01"
    assert node1.findtext("./macros/replica") == "node1"
    assert node2.findtext("./macros/replica") == "node2"


def test_multinode_fixture_pins_version_and_covers_required_engines() -> None:
    compose = yaml.safe_load((FIXTURE / "compose.yaml").read_text(encoding="utf-8"))
    assert "25.8.28.1" in compose["services"]["keeper"]["image"]
    assert set(compose["services"]) == {"keeper", "node1", "node2"}

    ddl = (FIXTURE / "fixture-ddl.sql").read_text(encoding="utf-8")
    for engine in (
        "ReplicatedMergeTree",
        "Distributed",
        "MergeTree",
        "ReplacingMergeTree",
        "TinyLog",
        "Memory",
    ):
        assert f"ENGINE = {engine}" in ddl


def test_multinode_fixture_is_wired_into_github_ci() -> None:
    workflow = yaml.safe_load(
        (ROOT / ".github" / "workflows" / "tests.yml").read_text(encoding="utf-8")
    )
    jobs = workflow["jobs"]
    job = jobs["clickhouse-multinode-25-8"]
    commands = [step.get("run", "") for step in job["steps"]]
    assert any("tools/run_multinode_clickhouse.py --remove" in command for command in commands)
