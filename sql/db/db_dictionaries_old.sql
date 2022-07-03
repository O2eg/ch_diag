select
	_shard_num,
	hostName() as host_name,
	database,
	name,
	type,
	status,
	element_count,
	query_count,
	hit_rate,
	bytes_allocated,
	formatReadableSize((bytes_allocated)) as pretty_bytes_allocated,
	last_successful_update_time,
	round(loading_duration, 2) as loading_duration,
	last_exception
from clusterAllReplicas(_CLUSTER_NAME, system.dictionaries)
order by _shard_num, host_name, database, name