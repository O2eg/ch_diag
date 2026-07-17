# System metrics [avg and max by last 3 days] (based on system.asynchronous_metric_log)

This instruction belongs to report item `historical_workload.workload_system_metrics`.

## What this item shows
- System metrics [avg and max by last 3 days] (based on system.asynchronous_metric_log).
- The table summarizes retained ClickHouse metric-log history over its stated lookback.

## What to watch
- Sustained pressure, high maxima at incident time, or node imbalance.

## Common fault causes
- CPU/memory/disk/network saturation, workload change, or background maintenance.

## Automatic evaluation
- Results depend on metric-log enablement, cadence, retention, and restart gaps.
- Averages smooth peaks and maxima do not show duration; no universal severity is assigned.

## Checklist
- Compare average versus maximum and current OS charts.
- Align metric-log timestamps with incident.
