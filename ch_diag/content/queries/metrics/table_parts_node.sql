SELECT
    hostName() AS host,
    sumIf(value, metric = 'TotalRowsOfMergeTreeTables') AS merge_tree_rows,
    sumIf(value, metric = 'TotalPartsOfMergeTreeTables') AS merge_tree_parts
FROM system.asynchronous_metrics
