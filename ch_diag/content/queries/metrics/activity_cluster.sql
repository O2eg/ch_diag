SELECT
    _shard_num AS shard_num,
    hostName() AS host,
    sumIf(value, metric = 'Query') AS current_queries,
    sumIf(value, metric = 'Merge') AS current_merges,
    sumIf(value, metric = 'PartMutation') AS current_mutations,
    sumIf(value, metric = 'DistributedSend') AS distributed_sends
FROM clusterAllReplicas({{cluster}}, system.metrics)
GROUP BY shard_num, host
ORDER BY shard_num, host
