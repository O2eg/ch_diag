WITH
    indexOf(ProfileEvents.Names, 'OSCPUVirtualTimeMicroseconds') AS cpu_index,
    indexOf(ProfileEvents.Names, 'OSCPUWaitMicroseconds') AS cpu_wait_index
SELECT
    hostName() AS host,
    event_time,
    thread_id,
    thread_name,
    query_id,
    user,
    query_duration_ms,
    if(cpu_index = 0, 0., ProfileEvents.Values[cpu_index] / 1000000.) AS cpu_seconds,
    if(cpu_wait_index = 0, 0., ProfileEvents.Values[cpu_wait_index] / 1000000.) AS cpu_wait_seconds,
    memory_usage,
    peak_memory_usage,
    substring(query, 1, 500) AS query
FROM clusterAllReplicas({{cluster}}, system.query_thread_log)
PREWHERE event_date >= today() - 1
WHERE event_time >= now() - INTERVAL 15 MINUTE
ORDER BY event_time DESC
LIMIT 1000
