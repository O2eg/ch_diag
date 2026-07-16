-- Generated standalone-node variant. Do not edit directly; see tools/generate_node_variants.py.
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
FROM (SELECT 1 AS _shard_num, 1 AS _replica_num, * FROM system.data_skipping_indices)
ORDER BY host_name, database, table, name
