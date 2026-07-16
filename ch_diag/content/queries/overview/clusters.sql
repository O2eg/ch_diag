SELECT
    cluster,
    shard_num,
    replica_num,
    host_name,
    host_address,
    port,
    is_local
FROM system.clusters
ORDER BY cluster, shard_num, replica_num
