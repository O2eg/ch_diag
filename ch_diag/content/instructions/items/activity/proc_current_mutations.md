# Current mutations (based on system.mutations)

This instruction belongs to report item `activity.proc_current_mutations`.

## What this item shows
- Current mutations (based on system.mutations).
- The table shows currently active or queued work, not a historical rate.

## What to watch
- Old unfinished mutations, many parts remaining, or repeated latest_fail_reason.

## Common fault causes
- Heavy ALTER DELETE/UPDATE, insufficient merge capacity, bad parts, disk, or replication trouble.

## Automatic evaluation
- This point-in-time table can miss work that starts and finishes outside collection.
- A nonempty result is not automatically unhealthy; elapsed time, progress, backlog, and errors determine significance.

## Checklist
- Read failure reason and affected parts.
- Correlate with merges, replication, and capacity before kill/restart.
