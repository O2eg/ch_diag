# Failed queries (based on system.query_log)

This instruction belongs to report item `errors.errors_queries`.

## What this item shows
- Failed queries (based on system.query_log).
- The result preserves bounded ClickHouse error evidence for root-cause correlation.

## What to watch
- repeated query/user/code combinations

## Common fault causes
- bad SQL, limits, timeout, permissions, memory, or remote shard; secondary errors may follow an earlier root failure

## Automatic evaluation
- Collection status only says whether the diagnostic query ran; returned error rows are incident evidence, not an OK result.
- An empty result may mean no matches, while unsupported, permission-denied, and log-retention gaps are distinct diagnostics.

## Checklist
- Group by code/message and locate the first occurrence.
- Correlate host/time with logs, query/table/replica, and resource charts.
