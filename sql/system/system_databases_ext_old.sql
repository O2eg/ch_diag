select
	_shard_num,
	hostName() as host_name,
	database,
	sum(rows) as total_rows,
	sum(bytes_on_disk) as total_bytes,
	formatReadableSize(total_bytes) as pretty_total_bytes
from (
	select
		_shard_num,
		hostName() as host_name,
		database,
		-- table,
		rows,
		bytes_on_disk
	from clusterAllReplicas(_CLUSTER_NAME, system.parts)
	where database not in ('INFORMATION_SCHEMA', 'information_schema') and active = 1
)	-- to avoid "Column `_shard_num` is not under aggregate function and not in GROUP BY"
group by _shard_num, host_name, database
order by _shard_num, total_bytes desc nulls last;