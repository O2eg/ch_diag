SELECT
    hostName() AS host,
    sumIf(value, event = 'Query') AS queries,
    sumIf(value, event = 'SelectQuery') AS selects,
    sumIf(value, event = 'InsertQuery') AS inserts,
    sumIf(value, event = 'FailedQuery') AS failed_queries
FROM system.events
