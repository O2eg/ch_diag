# Replication queue errors (based on system.replication_queue)

This instruction belongs to report item `errors.errors_replication_queue`.

## What this item shows
- Replication queue errors (based on system.replication_queue).
- The result preserves bounded ClickHouse error evidence for root-cause correlation.

## What to watch
- retried old tasks with the same exception

## Common fault causes
- missing/corrupt part, source replica, Keeper, network, or storage; secondary errors may follow an earlier root failure

## Automatic evaluation
- Collection status only says whether the diagnostic query ran; returned error rows are incident evidence, not an OK result.
- An empty result may mean no matches, while unsupported, permission-denied, and log-retention gaps are distinct diagnostics.

## Checklist
- Group by code/message and locate the first occurrence.
- Correlate host/time with logs, query/table/replica, and resource charts.
