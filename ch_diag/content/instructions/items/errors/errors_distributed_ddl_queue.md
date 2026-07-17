# Distributed DDL queue errors (based on system.distributed_ddl_queue)

This instruction belongs to report item `errors.errors_distributed_ddl_queue`.

## What this item shows
- Distributed DDL queue errors (based on system.distributed_ddl_queue).
- The result preserves bounded ClickHouse error evidence for root-cause correlation.

## What to watch
- persistent exception or unfinished hosts

## Common fault causes
- offline host, schema drift, timeout, Keeper, or incompatible DDL; secondary errors may follow an earlier root failure

## Automatic evaluation
- Collection status only says whether the diagnostic query ran; returned error rows are incident evidence, not an OK result.
- An empty result may mean no matches, while unsupported, permission-denied, and log-retention gaps are distinct diagnostics.

## Checklist
- Group by code/message and locate the first occurrence.
- Correlate host/time with logs, query/table/replica, and resource charts.
