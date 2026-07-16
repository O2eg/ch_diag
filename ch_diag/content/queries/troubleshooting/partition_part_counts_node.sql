SELECT
    database,
    table,
    partition_id,
    count() AS active_parts,
    active_parts > 100 AS exceeds_recommended_threshold,
    sum(rows) AS rows,
    sum(bytes_on_disk) AS bytes_on_disk,
    max(modification_time) AS latest_part_time
FROM system.parts
WHERE active AND database NOT IN ('system', 'INFORMATION_SCHEMA', 'information_schema')
GROUP BY database, table, partition_id
ORDER BY active_parts DESC, database, table, partition_id
LIMIT 1000
