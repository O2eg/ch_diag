select
	_shard_num,
	hostName() as host_name,
	database,
    table,
    node_name,
    replica_name,
	source_replica,
	type,
	is_currently_executing,
	last_exception,
    last_attempt_time,
    num_postponed,
    postpone_reason
from clusterAllReplicas(_CLUSTER_NAME, system.replication_queue)
order by _shard_num, host_name, database, table
limit 1000