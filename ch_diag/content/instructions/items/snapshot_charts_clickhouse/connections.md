# ClickHouse Client Connections

This instruction belongs to report item `snapshot_charts_clickhouse.connections`.

## What this item shows
- Current TCP and HTTP ClickHouse client connection gauges.
- They show concurrency, not connection creation/churn rate.

## What to watch
- Counts near configured limits or sustained unexplained growth.
- Application errors suggesting churn even when gauges look moderate.

## Common fault causes
- Leaks, missing pooling, bursts, long queries, slow clients, load balancers, or health checks.

## Automatic evaluation
- No fixed severity is assigned without effective limits.
- Short-lived churn may be missed.

## Checklist
- Compare with max_connections and client pool metrics.
- Check query concurrency and network/client errors.
