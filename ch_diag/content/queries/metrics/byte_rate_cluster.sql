SELECT
    _shard_num AS shard_num,
    hostName() AS host,
    sumIf(value, event = 'InsertedBytes') AS inserted_bytes,
    sumIf(value, event = 'SelectedBytes') AS read_bytes
FROM clusterAllReplicas({{cluster}}, system.events)
GROUP BY shard_num, host
ORDER BY shard_num, host
