SELECT
    event_time,
    database,
    table,
    part_name,
    error AS error_code,
    exception
FROM system.part_log
WHERE event_time >= now() - INTERVAL 1 DAY
  AND error != 0
ORDER BY event_time DESC
LIMIT 200
