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
	last_successful_update_time,
	loading_duration as loading_duration,
	last_exception
from clusterAllReplicas({{cluster}}, system.dictionaries)
order by _shard_num, host_name, database, name