SELECT
    hostName() AS host,
    event_time,
    thread_id,
    thread_name,
    query_id,
    user,
    ProfileEvents['OSReadBytes'] AS os_read_bytes,
    ProfileEvents['OSWriteBytes'] AS os_write_bytes,
    os_read_bytes + os_write_bytes AS os_io_bytes,
    peak_memory_usage,
    substring(query, 1, 500) AS query
FROM clusterAllReplicas({{cluster}}, system.query_thread_log)
PREWHERE event_date >= today() - 1
WHERE event_time >= now() - INTERVAL 15 MINUTE
ORDER BY event_time DESC
LIMIT 1000
