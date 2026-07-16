SELECT
    _shard_num AS shard_num,
    hostName() AS host,
    database,
    table,
    partition_id,
    count() AS active_parts,
    sum(rows) AS rows,
    sum(bytes_on_disk) AS bytes_on_disk,
    sum(data_compressed_bytes) AS data_compressed_bytes,
    sum(data_uncompressed_bytes) AS data_uncompressed_bytes,
    sum(primary_key_bytes_in_memory) AS primary_key_bytes_in_memory,
    sum(marks_bytes) AS marks_bytes
FROM clusterAllReplicas({{cluster}}, system.parts)
WHERE active AND database NOT IN ('system', 'INFORMATION_SCHEMA', 'information_schema')
GROUP BY shard_num, host, database, table, partition_id
ORDER BY bytes_on_disk DESC, shard_num, host, database, table, partition_id
LIMIT 1000
