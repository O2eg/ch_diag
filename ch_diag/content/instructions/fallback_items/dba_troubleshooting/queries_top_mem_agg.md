# Fallback: Query Memory Aggregates Without CPU Event Expansion

## What this item shows
- Normalized memory-heavy query aggregates without expanding ProfileEvents for CPU attribution.

## What to watch
- Query families with high total memory, duration, reads, or result volume.

## Common fault causes
- CPU event arrays or maps were unavailable or too expensive to expand within the primary collection budget.

## Automatic evaluation
- CPU totals are absent; this fallback supplies only the overlapping memory and workload evidence.

## Checklist
- Correlate the fallback rows with host CPU charts and inspect the recorded primary diagnostics before tuning.
