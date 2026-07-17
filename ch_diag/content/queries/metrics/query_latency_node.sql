SELECT
    hostName() AS host,
    sumIf(value, event = 'QueryTimeMicroseconds') AS query_time_us,
    sumIf(value, event = 'Query') AS queries
FROM system.events
