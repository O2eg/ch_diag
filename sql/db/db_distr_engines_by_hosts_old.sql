select
	_shard_num,
	host_name,
	database,
	engine,
	count(1) as total_tables
from (
	select
		_shard_num,
		hostName() as host_name,
		database,
		engine
	from clusterAllReplicas(_CLUSTER_NAME, system.tables)
	where database not in ('_system', 'system', 'information_schema', 'INFORMATION_SCHEMA')
) t
group by _shard_num, host_name, database, engine
order by _shard_num, host_name, database, engine