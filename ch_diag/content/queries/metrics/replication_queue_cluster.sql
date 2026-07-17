SELECT
    _shard_num AS shard_num,
    hostName() AS host,
    countIf(is_readonly) AS readonly_replicas,
    sum(queue_size) AS queue_size
FROM clusterAllReplicas({{cluster}}, system.replicas)
GROUP BY shard_num, host
ORDER BY shard_num, host
