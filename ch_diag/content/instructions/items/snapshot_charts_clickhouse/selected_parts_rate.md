# Selected Parts, Marks And Ranges

This instruction belongs to report item `snapshot_charts_clickhouse.selected_parts_rate`.

## What this item shows
- Rates of selected MergeTree parts, marks, and ranges from system.events.
- They expose index/pruning work initiated by queries.

## What to watch
- Many parts/marks per query or per useful row.
- Rapid growth after partition/schema changes.

## Common fault causes
- Too many small parts, fine partitions, weak ORDER BY pruning, FINAL, or filters that cannot use skipping indexes.

## Automatic evaluation
- Counter deltas are informational and reset-safe.
- High values can be legitimate analytics when latency/resources remain healthy.

## Checklist
- Normalize by query and row rates.
- Inspect partition part counts, EXPLAIN indexes, and offending normalized queries.
