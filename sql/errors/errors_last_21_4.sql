select
	_shard_num,
	hostName() as host_name,
	name,
	last_error_time,
	code,
	value,
	remote,
	last_error_message,
	last_error_time
from clusterAllReplicas(_CLUSTER_NAME, system.errors)
order by _shard_num, host_name, last_error_time desc
limit 100;