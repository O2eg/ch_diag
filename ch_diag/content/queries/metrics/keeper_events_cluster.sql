SELECT
    _shard_num AS shard_num,
    hostName() AS host,
    sumIf(value, match(event, 'ZooKeeper|Keeper')) AS keeper_events
FROM clusterAllReplicas({{cluster}}, system.events)
GROUP BY shard_num, host
ORDER BY shard_num, host
