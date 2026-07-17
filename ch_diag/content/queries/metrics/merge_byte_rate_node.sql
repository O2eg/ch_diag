SELECT
    hostName() AS host,
    sumIf(value, event = 'MergedUncompressedBytes') AS merged_bytes
FROM system.events
