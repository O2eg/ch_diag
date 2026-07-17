SELECT
    _shard_num AS shard_num,
    hostName() AS host,
    sumIf(value, event = 'NetworkReceiveBytes') AS network_receive_bytes,
    sumIf(value, event = 'NetworkSendBytes') AS network_send_bytes
FROM clusterAllReplicas({{cluster}}, system.events)
GROUP BY shard_num, host
ORDER BY shard_num, host
