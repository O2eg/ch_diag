SELECT
    _shard_num AS shard_num,
    hostName() AS host,
    sumIf(value, event = 'Query') AS queries,
    sumIf(value, event = 'SelectQuery') AS selects,
    sumIf(value, event = 'InsertQuery') AS inserts,
    sumIf(value, event = 'FailedQuery') AS failed_queries
FROM clusterAllReplicas({{cluster}}, system.events)
GROUP BY shard_num, host
ORDER BY shard_num, host
