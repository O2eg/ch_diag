SELECT
    _shard_num AS shard_num,
    hostName() AS host,
    count() AS replicas,
    countIf(is_readonly) AS readonly_replicas,
    sum(queue_size) AS queue_size,
    max(toUInt64OrZero(toString(absolute_delay))) AS maximum_delay_seconds
FROM clusterAllReplicas({{cluster}}, system.replicas)
GROUP BY shard_num, host
ORDER BY shard_num, host
