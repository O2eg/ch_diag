select
	_shard_num,
	host_name,
	database,
	name,
	any(engine) as engine,
	any(replaceRegexpAll(t2.create_table_query, 'PASSWORD\s\'.*?\'', '...')) as create_table_query,
	sum(rows) as total_rows,
	sum(bytes_on_disk) as total_bytes,
	formatReadableSize(total_bytes) as pretty_total_bytes
from (
	select
		_shard_num,
		hostName() as host_name,
		database,
		table,
		engine,
		rows,
		bytes_on_disk
	from clusterAllReplicas(test_cluster, system.parts)
	where database not in ('_system', 'system', 'information_schema', 'INFORMATION_SCHEMA')
		and active = 1
) t1
join (
	select
		_shard_num,
		hostName() as host_name,
		database,
		name,
		create_table_query
	from clusterAllReplicas(test_cluster, system.tables)
	where database not in ('_system', 'system', 'information_schema', 'INFORMATION_SCHEMA')
) t2 on
	t1._shard_num = t2._shard_num and
	t1.host_name = t2.host_name and
	t1.database = t2.database and
	t1.table = t2.name
group by _shard_num, host_name, database, name
order by total_bytes desc nulls last