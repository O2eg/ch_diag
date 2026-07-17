SELECT
    hostName() AS host,
    sumIf(value, event = 'InsertedRows') AS inserted_rows,
    sumIf(value, event = 'SelectedRows') AS read_rows
FROM system.events
