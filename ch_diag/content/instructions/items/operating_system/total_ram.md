# Total RAM Capacity

This instruction belongs to report item `operating_system.total_ram`. The item is backed by `operating_system.total_ram` (local host script).

## What this item shows
- Host total RAM capacity from `/proc/meminfo`, stored as exact bytes and displayed with an adaptive IEC unit.
- Sizing evidence for ClickHouse query memory limits, caches, background work, and connection concurrency.

## What to watch
- RAM smaller than expected for the instance class or hardware.
- Capacity mismatch across cluster nodes.
- Configured memory budgets that exceed physical RAM.

## Common fault causes
- Wrong VM flavor or container limit.
- Hardware replacement or BIOS memory issue.
- Configuration copied from a larger host.

## Automatic evaluation
- No severity is assigned because adequate capacity depends on workload and ClickHouse configuration.
- `/proc/meminfo` may describe the host rather than a container cgroup limit; validate container quotas separately.

## Checklist
- Confirm instance size or physical RAM inventory.
- Recalculate worst-case memory with query concurrency, `max_memory_usage`, caches, merges, and container limits.
- Compare with `Memory Information` for current availability.
