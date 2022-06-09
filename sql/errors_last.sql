select
	_shard_num,
	hostName() as host_name,
	name,
	any(last_error_time) as last_error_time,
	any(code) as code,
	any(value) as value,
	any(remote) as remote,
	any(last_error_message) as last_error_message
from clusterAllReplicas(_CLUSTER_NAME, system.errors)
group by _shard_num, host_name, name
order by _shard_num, host_name, last_error_time desc
limit 100;