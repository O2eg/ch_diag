# Replication errors (based on system.replicas)

This instruction belongs to report item `errors.errors_replicas`.

## What this item shows
- Replication errors (based on system.replicas).
- The result preserves bounded ClickHouse error evidence for root-cause correlation.

## What to watch
- read-only/session-expired/lost-part state

## Common fault causes
- Keeper, disk/network, or unavailable replicas; secondary errors may follow an earlier root failure

## Automatic evaluation
- Collection status only says whether the diagnostic query ran; returned error rows are incident evidence, not an OK result.
- An empty result may mean no matches, while unsupported, permission-denied, and log-retention gaps are distinct diagnostics.

## Checklist
- Group by code/message and locate the first occurrence.
- Correlate host/time with logs, query/table/replica, and resource charts.
