SELECT
    _shard_num AS shard_num,
    hostName() AS host,
    sumIf(value, event = 'QueryTimeMicroseconds') AS query_time_us,
    sumIf(value, event = 'Query') AS queries
FROM clusterAllReplicas({{cluster}}, system.events)
GROUP BY shard_num, host
ORDER BY shard_num, host
