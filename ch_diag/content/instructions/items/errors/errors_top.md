# Top 20 errors in cluster (based on system.errors)

This instruction belongs to report item `errors.errors_top`.

## What this item shows
- Top 20 errors in cluster (based on system.errors).
- The result preserves bounded ClickHouse error evidence for root-cause correlation.

## What to watch
- a new dominant code/message or rapidly increasing count

## Common fault causes
- query, storage, network, resource, or configuration failure; secondary errors may follow an earlier root failure

## Automatic evaluation
- Collection status only says whether the diagnostic query ran; returned error rows are incident evidence, not an OK result.
- An empty result may mean no matches, while unsupported, permission-denied, and log-retention gaps are distinct diagnostics.

## Checklist
- Group by code/message and locate the first occurrence.
- Correlate host/time with logs, query/table/replica, and resource charts.
