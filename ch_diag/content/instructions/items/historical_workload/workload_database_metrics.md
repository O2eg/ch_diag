# Database metrics [by last 3 days] (based on system.metric_log)

This instruction belongs to report item `historical_workload.workload_database_metrics`.

## What this item shows
- Database metrics [by last 3 days] (based on system.metric_log).
- The table summarizes retained ClickHouse metric-log history over its stated lookback.

## What to watch
- Throughput/latency/error shifts and a database dominating unexpectedly.

## Common fault causes
- Traffic change, retries, expensive queries, merges, or resource saturation.

## Automatic evaluation
- Results depend on metric-log enablement, cadence, retention, and restart gaps.
- Averages smooth peaks and maxima do not show duration; no universal severity is assigned.

## Checklist
- Correlate with query rankings and current charts.
- Compare nodes and deployment timeline.
