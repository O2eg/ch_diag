select
	_shard_num,
	hostName() as host_name,
	query_start_time,
	query_duration_ms as duration_ms,
	substringUTF8(query, 1, 15000) as query,
	is_initial_query as is_initial,
	type,
	read_rows,
	read_bytes,
	formatReadableSize(read_bytes) as p_read_bytes,
	result_rows,
	result_bytes,
	formatReadableSize(result_bytes) as p_result_bytes,
	memory_usage,
	formatReadableSize(memory_usage) as p_memory_usage
from clusterAllReplicas(_CLUSTER_NAME, system.query_log)
where
	exception_code = 0 and
	query_start_time > now() - interval 3 day and
	type = 'QueryFinish'
order by memory_usage desc
limit 30;