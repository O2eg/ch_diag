# Storage Breakdown By Partition

This instruction belongs to report item `dba_troubleshooting.storage_breakdown`.

## What this item shows
- Rows, parts, bytes, marks, and primary-index memory by table partition.

## What to watch
- Many parts, disproportionate marks/index memory, or unexpected partition growth.

## Common fault causes
- Small inserts, fine partitioning, retention gaps, weak compression, or merge backlog.

## Automatic evaluation
- Raw inventory is informational; detached/temporary data may require other evidence.

## Checklist
- Compare with filesystem free space and aggregate table charts.
- Inspect the largest/problem partitions, TTL, part creation, and merges.
