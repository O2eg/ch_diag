SELECT
	_shard_num,
	hostName() as host_name,
    database,
    table,
    round(elapsed, 1) as elapsed,
    round(100 * progress, 1) as progress,
    partition_id,
    result_part_name,
    result_part_path,
    total_size_bytes_compressed,
    bytes_read_compressed,
    source_replica_path,
    source_replica_hostname,
    source_replica_port,
    interserver_scheme,
    to_detached,
    thread_id
from clusterAllReplicas(_CLUSTER_NAME, system.replicated_fetches)
order by elapsed desc
limit 1000