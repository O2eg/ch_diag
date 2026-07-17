SELECT
    hostName() AS host,
    countIf(event_type = 'NewPart') AS created_parts
FROM system.part_log
