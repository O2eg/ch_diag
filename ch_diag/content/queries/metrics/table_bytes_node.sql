SELECT
    hostName() AS host,
    sumIf(value, metric = 'TotalBytesOfMergeTreeTables') AS merge_tree_bytes
FROM system.asynchronous_metrics
