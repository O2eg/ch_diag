SELECT
    _shard_num AS shard_num,
    hostName() AS host,
    sumIf(value, event = 'ReplicatedPartFetches') AS replicated_part_fetches,
    sumIf(value, event = 'ReplicatedPartFailedFetches') AS replicated_part_failed_fetches,
    sumIf(value, event = 'ReplicatedPartMerges') AS replicated_part_merges,
    sumIf(value, event = 'ReplicatedDataLoss') AS replicated_data_loss
FROM clusterAllReplicas({{cluster}}, system.events)
GROUP BY shard_num, host
ORDER BY shard_num, host
