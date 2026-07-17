SELECT
    cityHash64(query) AS normalized_query_hash,
    count() AS executions,
    avg(query_duration_ms) AS average_duration_ms,
    quantile(0.95)(query_duration_ms) AS p95_duration_ms,
    sum(read_rows) AS read_rows,
    sum(read_bytes) AS read_bytes,
    max(event_time) AS last_execution_time
FROM system.query_log
WHERE type = 'QueryFinish'
  AND event_time >= now() - INTERVAL 1 DAY
GROUP BY normalized_query_hash
ORDER BY executions DESC, normalized_query_hash
LIMIT 100
