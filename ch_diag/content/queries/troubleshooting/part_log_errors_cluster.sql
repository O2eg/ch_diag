SELECT
    _shard_num AS shard_num,
    hostName() AS host,
    event_time,
    database,
    table,
    part_name,
    error AS error_code,
    exception
FROM clusterAllReplicas({{cluster}}, system.part_log)
WHERE event_time >= now() - INTERVAL 1 DAY
  AND error != 0
ORDER BY event_time DESC, shard_num, host
LIMIT 200
