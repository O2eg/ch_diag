# Current merges (based on system.merges)

This instruction belongs to report item `activity.proc_current_merges`.

## What this item shows
- Current merges (based on system.merges).
- The table shows currently active or queued work, not a historical rate.

## What to watch
- Slow/no-progress merges, high concurrency, or large merges aligned with disk/query pressure.

## Common fault causes
- Ingestion backlog, TTL/mutations, slow storage, or oversized parts.

## Automatic evaluation
- This point-in-time table can miss work that starts and finishes outside collection.
- A nonempty result is not automatically unhealthy; elapsed time, progress, backlog, and errors determine significance.

## Checklist
- Compare progress across captures and merge-rate charts.
- Check disk latency/utilization and partition parts.
