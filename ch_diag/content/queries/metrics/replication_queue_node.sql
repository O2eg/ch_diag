SELECT
    hostName() AS host,
    countIf(is_readonly) AS readonly_replicas,
    sum(queue_size) AS queue_size
FROM system.replicas
