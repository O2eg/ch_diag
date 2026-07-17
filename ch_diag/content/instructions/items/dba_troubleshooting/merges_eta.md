# Merges In Progress With ETA

This instruction belongs to report item `dba_troubleshooting.merges_eta`.

## What this item shows
- Current merges with progress and division-safe estimated remaining time.

## What to watch
- Very long ETA, no progress across captures, excess concurrency, or merges consuming capacity.

## Common fault causes
- Slow storage, oversized parts, mutations/TTL, resource contention, or unstable early estimates.

## Automatic evaluation
- ETA is omitted when progress/rate is insufficient and never divides by zero.
- It is an estimate, not a deadline.

## Checklist
- Compare successive progress.
- Correlate merge throughput, disk latency/utilization, and background pools before cancellation.
