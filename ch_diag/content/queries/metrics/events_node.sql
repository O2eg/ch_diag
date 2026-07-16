SELECT
    hostName() AS host,
    sumIf(value, event = 'Query') AS queries,
    sumIf(value, event = 'SelectQuery') AS selects,
    sumIf(value, event = 'InsertedRows') AS inserted_rows,
    sumIf(value, event = 'InsertedBytes') AS inserted_bytes,
    sumIf(value, event = 'SelectedRows') AS read_rows,
    sumIf(value, event = 'SelectedBytes') AS read_bytes,
    sumIf(value, event IN ('FailedQuery', 'FailedSelectQuery')) AS failed_queries,
    sumIf(value, match(event, 'ZooKeeper|Keeper')) AS keeper_events
FROM system.events
