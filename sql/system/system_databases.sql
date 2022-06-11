select
	_shard_num,
	hostName() as host_name,
	name,
	engine
from clusterAllReplicas(_CLUSTER_NAME, system.databases)
where name not in ('INFORMATION_SCHEMA', 'information_schema')
order by _shard_num, host_name, name