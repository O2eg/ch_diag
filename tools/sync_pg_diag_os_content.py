#!/usr/bin/env python3
"""Review/sync the vendored DB-independent Linux scripts from pg_diag."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import shutil

import yaml


FILES = (
    "cpu_info.sh", "df_h.sh", "etc_fstab.sh", "etc_os_release.sh", "ip_br_addr.sh",
    "lshw_bridge.sh", "lshw_bus.sh", "lshw_communication.sh", "lshw_disk.sh",
    "lshw_display.sh", "lshw_generic.sh", "lshw_input.sh", "lshw_memory.sh",
    "lshw_multimedia.sh", "lshw_network.sh", "lshw_power.sh", "lshw_processor.sh",
    "lshw_storage.sh", "lshw_system.sh", "lshw_volume.sh", "mount.sh",
    "sys_memory_total.sh", "sysctl_net_ipv4_tcp.sh", "sysctl_net_ipv4_udp.sh",
    "sysctl_vm.sh", "total_ram.sh", "uname_a.sh",
)
OS_METRICS = (
    "os.cpu_utilization",
    "os.cpu_load",
    "os.memory_usage",
    "os.memory_pressure",
    "os.disk_read_throughput",
    "os.disk_write_throughput",
    "os.disk_iops",
    "os.disk_utilization",
    "os.disk_latency",
    "os.network_receive_throughput",
    "os.network_transmit_throughput",
    "os.network_packets",
)
METRIC_CONTRACT_KEYS = ("title", "source_sampler", "partition_by", "series", "chart")


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def metric_contract(manifest: dict[str, object]) -> dict[str, object]:
    return {key: manifest[key] for key in METRIC_CONTRACT_KEYS if key in manifest}


def metric_digest(manifest: dict[str, object]) -> str:
    serialized = yaml.safe_dump(
        metric_contract(manifest),
        sort_keys=False,
        allow_unicode=True,
    ).encode("utf-8")
    return hashlib.sha256(serialized).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pg-diag-checkout", required=True, type=Path)
    parser.add_argument("--sync", action="store_true", help="copy donor files after review")
    args = parser.parse_args()
    repo = Path(__file__).resolve().parents[1]
    donor = args.pg_diag_checkout.resolve()
    donor_root = donor / "pg_diag" / "content" / "scripts" / "os"
    target_root = repo / "ch_diag" / "content" / "scripts" / "os"
    entries = []
    changed = []
    for name in FILES:
        source = donor_root / name
        target = target_root / name
        if not source.is_file():
            raise SystemExit(f"missing donor file: {source}")
        if args.sync:
            shutil.copy2(source, target)
        source_hash = digest(source)
        target_hash = digest(target)
        if source_hash != target_hash:
            changed.append(name)
        entries.append(
            {
                "source": f"pg_diag/content/scripts/os/{name}",
                "target": f"scripts/os/{name}",
                "sha256": target_hash,
                "donor_sha256": source_hash,
            }
        )

    donor_metrics_path = donor / "pg_diag" / "content" / "metrics.yaml"
    target_metrics_path = repo / "ch_diag" / "content" / "metrics.yaml"
    donor_metrics = yaml.safe_load(donor_metrics_path.read_text(encoding="utf-8"))["metrics"]
    target_document = yaml.safe_load(target_metrics_path.read_text(encoding="utf-8"))
    target_metrics = target_document["metrics"]
    metric_entries = []
    for metric_id in OS_METRICS:
        donor_manifest = donor_metrics[metric_id]
        target_manifest = target_metrics[metric_id]
        if args.sync:
            for key in METRIC_CONTRACT_KEYS:
                if key in donor_manifest:
                    target_manifest[key] = donor_manifest[key]
                else:
                    target_manifest.pop(key, None)
        donor_hash = metric_digest(donor_manifest)
        target_hash = metric_digest(target_manifest)
        if donor_hash != target_hash:
            changed.append(metric_id)
        metric_entries.append(
            {
                "id": metric_id,
                "sha256": target_hash,
                "donor_sha256": donor_hash,
            }
        )
    if args.sync:
        target_metrics_path.write_text(
            yaml.safe_dump(target_document, sort_keys=False, allow_unicode=True, width=100),
            encoding="utf-8",
        )
    lock = {
        "upstream": {
            "repository": "https://github.com/O2eg/pg_diag",
            "tag": "v0.9.0",
            "commit": "22b411d4c44ddaeac55bcde87c35f9229b1eed85",
        },
        "files": entries,
        "metric_contracts": metric_entries,
        "allowed_differences": [],
    }
    lock_path = repo / "ch_diag" / "content" / "UPSTREAM_OS_CONTENT.lock.yaml"
    lock_path.write_text(
        yaml.safe_dump(lock, sort_keys=False, allow_unicode=True, width=110),
        encoding="utf-8",
    )
    if changed:
        print("files differing from donor: " + ", ".join(changed))
        return 1
    print(
        f"all {len(FILES)} OS scripts and {len(OS_METRICS)} OS metric contracts "
        f"match donor; wrote {lock_path}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
