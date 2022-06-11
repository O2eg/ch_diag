select
	_shard_num,
	hostName() as host_name,
	database,
    table,
    is_blocked,
	error_count,
	last_exception
from clusterAllReplicas(_CLUSTER_NAME, system.distribution_queue)
WHERE error_count > 0 or is_blocked = 1
order by error_count desc