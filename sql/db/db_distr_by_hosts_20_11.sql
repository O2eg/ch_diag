select
	_shard_num,
	hostName() as host_name,
	database,
	count(1) as total_tables,
	sum(toInt64(total_rows)) as total_rows,
	sum(toInt64(total_bytes)) as _total_bytes,
	formatReadableSize(sum(toInt64(total_bytes))) as pretty_total_bytes
from clusterAllReplicas(_CLUSTER_NAME, system.tables)
where database not in ('_system', 'system', 'information_schema', 'INFORMATION_SCHEMA')
group by _shard_num, host_name, database
order by _shard_num, host_name, database