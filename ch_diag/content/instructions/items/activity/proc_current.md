# Current processes (based on system.processes)

This instruction belongs to report item `activity.proc_current`.

## What this item shows
- Current processes (based on system.processes).
- The table shows currently active or queued work, not a historical rate.

## What to watch
- Long/high-memory queries, many similar concurrent queries, or work stalled during resource pressure.

## Common fault causes
- Expensive scans/joins, client concurrency, remote-shard stalls, or saturation.

## Automatic evaluation
- This point-in-time table can miss work that starts and finishes outside collection.
- A nonempty result is not automatically unhealthy; elapsed time, progress, backlog, and errors determine significance.

## Checklist
- Resolve query_id/user and inspect plan/settings securely.
- Compare query-log rankings and CPU/memory/I/O.
