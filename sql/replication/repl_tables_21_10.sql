SELECT
	_shard_num,
	hostName() as host_name,
    database,
    table,
    absolute_delay,
	replica_path,
    is_leader,
    is_readonly,
	is_session_expired,
	future_parts,
	parts_to_check,
    queue_size,
    inserts_in_queue,
    merges_in_queue,
	log_max_index,
	log_pointer,
    total_replicas,
    active_replicas,
    toString(replica_is_active) as replica_is_active,
    last_queue_update_exception,
    zookeeper_exception
from clusterAllReplicas(_CLUSTER_NAME, system.replicas)
ORDER BY absolute_delay DESC
LIMIT 5000