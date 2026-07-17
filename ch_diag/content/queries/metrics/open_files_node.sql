SELECT
    hostName() AS host,
    sumIf(value, metric = 'OSOpenFiles') AS open_files
FROM system.asynchronous_metrics
