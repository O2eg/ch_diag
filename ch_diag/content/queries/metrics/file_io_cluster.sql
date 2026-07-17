SELECT
    _shard_num AS shard_num,
    hostName() AS host,
    sumIf(value, event = 'ReadBufferFromFileDescriptorReadBytes') AS file_read_bytes,
    sumIf(value, event = 'WriteBufferFromFileDescriptorWriteBytes') AS file_write_bytes
FROM clusterAllReplicas({{cluster}}, system.events)
GROUP BY shard_num, host
ORDER BY shard_num, host
