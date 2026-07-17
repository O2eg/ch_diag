-- Generated standalone-node variant. Do not edit directly; see tools/generate_node_variants.py.
SELECT
    _shard_num,
    hostName() AS host_name,
    current_database AS current_db,
    normalized_query_hash,
    sum(query_duration_ms) AS total_duration_ms,
    count() AS query_times,
    groupUniqArray(is_initial_query) AS is_initial,
    sum(read_rows) AS total_read_rows,
    sum(read_bytes) AS total_read_bytes,
    sum(result_rows) AS total_result_rows,
    sum(result_bytes) AS total_result_bytes,
    sum(memory_usage) AS total_memory_usage,
    event_name,
    sum(event_value) AS total_profile_event_value
FROM (SELECT 1 AS _shard_num, 1 AS _replica_num, * FROM system.query_log)
ARRAY JOIN
    mapKeys(ProfileEvents) AS event_name,
    mapValues(ProfileEvents) AS event_value
WHERE
    exception_code = 0
    AND event_time > now() - INTERVAL 3 DAY
    AND type = 'QueryFinish'
GROUP BY
    _shard_num,
    host_name,
    current_db,
    normalized_query_hash,
    event_name
ORDER BY total_duration_ms DESC, total_profile_event_value DESC
LIMIT 500
