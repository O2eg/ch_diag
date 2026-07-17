SELECT
    _shard_num,
    hostName() AS host_name,
    database,
    table,
    name,
    type,
    type_full,
    expr,
    granularity,
    data_compressed_bytes,
    data_uncompressed_bytes,
    marks_bytes
FROM clusterAllReplicas({{cluster}}, system.data_skipping_indices)
ORDER BY host_name, database, table, name
