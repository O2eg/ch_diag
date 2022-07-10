select
	_shard_num,
	host_name,
	database,
	count(1) as total_tables,
	sum(toInt64(rows)) as total_rows,
	sum(toInt64(bytes_on_disk)) as total_bytes,
	formatReadableSize(total_bytes) as pretty_total_bytes
from (
	select
		_shard_num,
		hostName() as host_name,
		database,
		rows,
		bytes_on_disk
	from clusterAllReplicas(_CLUSTER_NAME, system.parts)
	where database not in ('_system', 'system', 'information_schema', 'INFORMATION_SCHEMA')
		and active = 1
)
group by _shard_num, host_name, database
order by _shard_num, host_name, database