# Mutation erros (based on system.mutations)

This instruction belongs to report item `errors.errors_mutations`.

## What this item shows
- Mutation erros (based on system.mutations).
- The result preserves bounded ClickHouse error evidence for root-cause correlation.

## What to watch
- old mutations, parts remaining, or repeated failure reason

## Common fault causes
- invalid mutation, disk/part, resource, or replication problem; secondary errors may follow an earlier root failure

## Automatic evaluation
- Collection status only says whether the diagnostic query ran; returned error rows are incident evidence, not an OK result.
- An empty result may mean no matches, while unsupported, permission-denied, and log-retention gaps are distinct diagnostics.

## Checklist
- Group by code/message and locate the first occurrence.
- Correlate host/time with logs, query/table/replica, and resource charts.
