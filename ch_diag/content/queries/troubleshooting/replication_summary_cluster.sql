SELECT
    _shard_num AS shard_num,
    hostName() AS host,
    database,
    table,
    is_readonly,
    is_session_expired,
    queue_size,
    inserts_in_queue,
    merges_in_queue,
    part_mutations_in_queue,
    absolute_delay AS delay_seconds,
    total_replicas,
    active_replicas
FROM clusterAllReplicas({{cluster}}, system.replicas)
ORDER BY is_readonly DESC, queue_size DESC, delay_seconds DESC, shard_num, host, database, table
LIMIT 1000
