SELECT
    hostName() AS host,
    sumIf(value, event = 'MergedRows') AS merged_rows
FROM system.events
