select
    _shard_num,
    hostName() as host_name,
    database,
    table,
    engine,
    is_leader,
    is_session_expired,
    is_readonly,
    replica_name,
    replica_path,
    queue_size,
    absolute_delay,
    total_replicas,
    active_replicas,
    zookeeper_exception
from clusterAllReplicas(_CLUSTER_NAME, system.replicas)
where
	zookeeper_exception != '' or
	is_readonly != 0 or
	is_session_expired != 0
order by _shard_num, host_name, database, table