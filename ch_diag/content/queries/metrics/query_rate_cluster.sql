SELECT
    _shard_num AS shard_num,
    hostName() AS host,
    toUInt32(now()) - uptime() AS server_start_epoch,
    sumIf(value, event = 'Query') AS queries,
    sumIf(value, event = 'SelectQuery') AS selects,
    sumIf(value, event = 'InsertQuery') AS inserts,
    sumIf(value, event = 'FailedQuery') AS failed_queries
FROM clusterAllReplicas({{cluster}}, system.events)
GROUP BY shard_num, host, server_start_epoch
ORDER BY shard_num, host
