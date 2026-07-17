SELECT
    hostName() AS host,
    sumIf(value, metric = 'MemoryTracking') AS memory_bytes
FROM system.metrics
