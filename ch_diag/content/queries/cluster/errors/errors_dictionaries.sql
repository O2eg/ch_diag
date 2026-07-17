select
	_shard_num,
	hostName() as host_name,
	database,
	name,
	type,
	status,
	last_successful_update_time,
	loading_duration as loading_duration,
	last_exception
from clusterAllReplicas({{cluster}}, system.dictionaries)
WHERE status in ('FAILED', 'FAILED_AND_RELOADING')
order by _shard_num, host_name, database, name