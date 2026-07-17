SELECT
    _shard_num AS shard_num,
    hostName() AS host,
    sumIf(value, metric = 'ReplicatedFetch') AS replicated_fetches,
    sumIf(value, metric = 'ReplicatedSend') AS replicated_sends
FROM clusterAllReplicas({{cluster}}, system.metrics)
GROUP BY shard_num, host
ORDER BY shard_num, host
