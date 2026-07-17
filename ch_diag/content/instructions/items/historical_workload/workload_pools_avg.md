# Pools utilization [avg by last week] (based on system.metric_log)

This instruction belongs to report item `historical_workload.workload_pools_avg`.

## What this item shows
- Pools utilization [avg by last week] (based on system.metric_log).
- The table summarizes retained ClickHouse metric-log history over its stated lookback.

## What to watch
- Pools with persistently high average use or strong host imbalance.

## Common fault causes
- Sustained merge/replication/query pressure, undersized pools, or slow dependencies.

## Automatic evaluation
- Results depend on metric-log enablement, cadence, retention, and restart gaps.
- Averages smooth peaks and maxima do not show duration; no universal severity is assigned.

## Checklist
- Compare with weekly maxima and current pool chart.
- Check log gaps and restarts before interpreting zero.
