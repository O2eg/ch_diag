# Disk Write Throughput

This instruction belongs to report item `snapshot_charts_os.os_disk_write_throughput`. The item is backed by `os.disk_write_throughput` (snapshot metric).

## What this item shows
- Write throughput by block device over time.
- Which device receives writes during the capture window.

## What to watch
- Sustained high writes on ClickHouse data, temporary, or log devices.
- Write spikes during merges, mutations, replication recovery, or bulk inserts.
- Writes aligned with rapid part creation or merge backlog.

## Common fault causes
- New part creation and background merges.
- Mutations, TTL processing, and replication fetches.
- Bulk inserts and temporary query spill.
- Backups or materialized-view fan-out.

## Automatic evaluation
- Values come from interval iostat reports and are informational; throughput alone does not indicate saturation.
- The first since-boot iostat report is discarded.

## Checklist
- Map devices to ClickHouse data, temporary, log, and backup paths.
- Compare with part creation, merge throughput, current mutations, and replication activity.
- Check latency when throughput is high.
