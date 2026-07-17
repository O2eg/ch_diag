# Failed dictionaries (based on system.dictionaries)

This instruction belongs to report item `errors.errors_dictionaries`.

## What this item shows
- Failed dictionaries (based on system.dictionaries).
- The result preserves bounded ClickHouse error evidence for root-cause correlation.

## What to watch
- failed/stale status and repeated exception

## Common fault causes
- source credentials/network, schema mismatch, or dictionary config; secondary errors may follow an earlier root failure

## Automatic evaluation
- Collection status only says whether the diagnostic query ran; returned error rows are incident evidence, not an OK result.
- An empty result may mean no matches, while unsupported, permission-denied, and log-retention gaps are distinct diagnostics.

## Checklist
- Group by code/message and locate the first occurrence.
- Correlate host/time with logs, query/table/replica, and resource charts.
