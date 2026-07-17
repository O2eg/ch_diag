SELECT
    _shard_num AS shard_num,
    hostName() AS host,
    sumIf(value, event = 'InsertedRows') AS inserted_rows,
    sumIf(value, event = 'SelectedRows') AS read_rows
FROM clusterAllReplicas({{cluster}}, system.events)
GROUP BY shard_num, host
ORDER BY shard_num, host
