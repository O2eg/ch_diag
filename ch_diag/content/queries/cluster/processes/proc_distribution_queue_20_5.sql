select
	_shard_num,
	hostName() as host_name,
	database,
	table,
	data_compressed_bytes,
	is_blocked,
	error_count,
	last_exception
from clusterAllReplicas({{cluster}}, system.distribution_queue)
order by _shard_num, host_name, database, table
limit 1000