# ClickHouse Query Rate

This instruction belongs to report item `snapshot_charts_clickhouse.query_rate`.

## What this item shows
- Per-second rates of Query, SelectQuery, InsertQuery, and FailedQuery counters from system.events.
- Each line is a counter delta divided by real elapsed time.

## What to watch
- Failure spikes, traffic-mix changes, or throughput falling while latency/concurrency rises.

## Common fault causes
- Traffic bursts, retries, deployments, client timeout loops, or server resource saturation.

## Automatic evaluation
- Counter reset/restart creates a gap; an idle valid interval can be zero.
- Collection status is data quality, not workload health.

## Checklist
- Correlate failures with Errors/query_log.
- Compare rate with latency, activity, CPU, memory, and I/O.
