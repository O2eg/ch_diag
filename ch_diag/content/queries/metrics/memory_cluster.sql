SELECT
    _shard_num AS shard_num,
    hostName() AS host,
    sumIf(value, metric = 'MemoryTracking') AS memory_bytes
FROM clusterAllReplicas({{cluster}}, system.metrics)
GROUP BY shard_num, host
ORDER BY shard_num, host
