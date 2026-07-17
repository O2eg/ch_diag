SELECT
    _shard_num AS shard_num,
    hostName() AS host,
    sumIf(value, metric = 'TCPConnection') AS tcp_connections,
    sumIf(value, metric = 'HTTPConnection') AS http_connections
FROM clusterAllReplicas({{cluster}}, system.metrics)
GROUP BY shard_num, host
ORDER BY shard_num, host
