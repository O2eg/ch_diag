SELECT
    hostName() AS host,
    sumIf(value, event = 'InsertedBytes') AS inserted_bytes,
    sumIf(value, event = 'SelectedBytes') AS read_bytes
FROM system.events
