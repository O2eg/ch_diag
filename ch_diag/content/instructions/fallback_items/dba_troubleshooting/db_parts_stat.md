# Fallback: Bounded Data-Part Statistics

## What this item shows
- Coarser table and part statistics when partition-level storage aggregation cannot complete.

## What to watch
- Tables with many parts, large byte volume, or uneven active-part distribution.

## Common fault causes
- A large `system.parts` population made partition-level grouping exceed the primary timeout or read budget.

## Automatic evaluation
- Partition-level storage, marks, and primary-index detail are not preserved by this degraded source.

## Checklist
- Review the primary failure and use the bounded table-level evidence to narrow a later targeted partition query.
