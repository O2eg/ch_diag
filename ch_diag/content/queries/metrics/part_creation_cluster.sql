SELECT
    _shard_num AS shard_num,
    hostName() AS host,
    countIf(event_type = 'NewPart') AS created_parts
FROM clusterAllReplicas({{cluster}}, system.part_log)
GROUP BY shard_num, host
ORDER BY shard_num, host
