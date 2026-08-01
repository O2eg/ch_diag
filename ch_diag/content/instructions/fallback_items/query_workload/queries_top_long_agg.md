# Fallback: Top Long Queries Without ProfileEvents Expansion

## What this item shows
- Normalized long-query aggregates without expanding per-query ProfileEvents.

## What to watch
- Query families with high total duration, read volume, result volume, or memory use.

## Common fault causes
- ProfileEvents arrays or maps were unavailable, incompatible, or too expensive to expand within the primary budget.

## Automatic evaluation
- CPU and individual ProfileEvents attribution is absent, while the coarser duration and I/O aggregates remain usable.

## Checklist
- Confirm the primary failure kind and use other CPU, disk, and query-memory items for the missing event detail.
