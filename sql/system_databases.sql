select
	_shard_num,
	hostName() as host_name,
	groupArray(name) as dbs
from clusterAllReplicas(_CLUSTER_NAME, system.databases)
where name not in ('INFORMATION_SCHEMA', 'information_schema')
group by _shard_num, host_name
order by _shard_num, host_name;