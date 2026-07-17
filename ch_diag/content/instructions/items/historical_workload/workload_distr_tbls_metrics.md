# Distributed tables metrics [by last 3 days] (based on system.metric_log)

This instruction belongs to report item `historical_workload.workload_distr_tbls_metrics`.

## What this item shows
- Distributed tables metrics [by last 3 days] (based on system.metric_log).
- The table summarizes retained ClickHouse metric-log history over its stated lookback.

## What to watch
- Persistent distributed-send backlog, failures, or host/table imbalance.

## Common fault causes
- Remote shard/network failure, async insert bursts, DNS/auth, or disk pressure.

## Automatic evaluation
- Results depend on metric-log enablement, cadence, retention, and restart gaps.
- Averages smooth peaks and maxima do not show duration; no universal severity is assigned.

## Checklist
- Compare current distribution queue/errors and topology.
- Inspect remote shards for the incident interval.
