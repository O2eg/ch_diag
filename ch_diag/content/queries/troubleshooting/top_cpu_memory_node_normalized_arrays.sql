WITH 'OSCPUVirtualTimeMicroseconds' AS cpu_event
SELECT
    normalized_query_hash,
    count() AS executions,
    sum(query_duration_ms) AS total_duration_ms,
    max(memory_usage) AS peak_memory_bytes,
    sum(read_rows) AS read_rows,
    sum(read_bytes) AS read_bytes,
    sum(if(
        indexOf(ProfileEvents.Names, cpu_event) = 0,
        toUInt64(0),
        ProfileEvents.Values[indexOf(ProfileEvents.Names, cpu_event)]
    )) AS cpu_microseconds,
    max(event_time) AS last_execution_time
FROM system.query_log
WHERE type = 'QueryFinish'
  AND event_time >= now() - INTERVAL 1 DAY
  AND normalized_query_hash != 0
GROUP BY normalized_query_hash
ORDER BY cpu_microseconds DESC, peak_memory_bytes DESC
LIMIT 100
