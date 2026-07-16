SELECT
    hostName() AS host,
    count() AS replicas,
    countIf(is_readonly) AS readonly_replicas,
    sum(queue_size) AS queue_size,
    max(toUInt64OrZero(toString(absolute_delay))) AS maximum_delay_seconds
FROM system.replicas
