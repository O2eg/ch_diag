select
	_shard_num,
	hostName() as host_name,
	query_start_time,
	query_duration_ms as duration_ms,
	substringUTF8(query, 1, 15000) as query,
	is_initial_query as is_initial,
	read_rows,
	read_bytes,
	result_rows,
	result_bytes,
	memory_usage
from clusterAllReplicas({{cluster}}, system.query_log)
where
	exception_code = 0 and
	query_start_time > now() - interval 3 day and
	type = 'QueryFinish'
order by query_duration_ms desc
limit 30;
