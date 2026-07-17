SELECT
    _shard_num AS shard_num,
    hostName() AS host,
    sumIf(value, metric = 'OSOpenFiles') AS open_files
FROM clusterAllReplicas({{cluster}}, system.asynchronous_metrics)
GROUP BY shard_num, host
ORDER BY shard_num, host
