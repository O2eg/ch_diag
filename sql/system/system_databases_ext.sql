select
	_shard_num,
	hostName() as host_name,
	database,
	sum(total_rows) as total_rows,
	sum(total_bytes) as total_bytes,
	formatReadableSize(total_bytes) as pretty_total_bytes
from clusterAllReplicas(_CLUSTER_NAME, system.tables)
where database not in ('INFORMATION_SCHEMA', 'information_schema')
group by _shard_num, host_name, database
order by _shard_num, total_bytes desc nulls last;