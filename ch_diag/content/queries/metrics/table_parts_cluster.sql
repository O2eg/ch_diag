SELECT
    _shard_num AS shard_num,
    hostName() AS host,
    sumIf(value, metric = 'TotalRowsOfMergeTreeTables') AS merge_tree_rows,
    sumIf(value, metric = 'TotalPartsOfMergeTreeTables') AS merge_tree_parts
FROM clusterAllReplicas({{cluster}}, system.asynchronous_metrics)
GROUP BY shard_num, host
ORDER BY shard_num, host
