SELECT
    hostName() AS host,
    sumIf(value, metric = 'TCPConnection') AS tcp_connections,
    sumIf(value, metric = 'HTTPConnection') AS http_connections
FROM system.metrics
