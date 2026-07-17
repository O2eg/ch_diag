# Pools utilization [max by last week] (based on system.metric_log)

This instruction belongs to report item `historical_workload.workload_pools_max`.

## What this item shows
- Pools utilization [max by last week] (based on system.metric_log).
- The table summarizes retained ClickHouse metric-log history over its stated lookback.

## What to watch
- Pools repeatedly reaching capacity even when averages are modest.

## Common fault causes
- Bursty ingestion/recovery/mutations/distributed sends or pool mismatch.

## Automatic evaluation
- Results depend on metric-log enablement, cadence, retention, and restart gaps.
- Averages smooth peaks and maxima do not show duration; no universal severity is assigned.

## Checklist
- Compare maximum with average and actual backlog.
- Do not resize from one isolated maximum.
