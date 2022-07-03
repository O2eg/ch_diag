select
	_shard_num,
	hostName() as host_name,
	current_database as current_db,
	count(1) as query_times,
	sum(read_rows) as total_read_rows,
	sum(read_bytes) as total_read_bytes,
	formatReadableSize(sum(read_bytes)) as p_read_bytes,
	sum(result_rows) as total_result_rows,
	sum(result_bytes) as total_result_bytes,
	formatReadableSize(sum(result_bytes)) as p_total_result_bytes,
	sum(memory_usage) as total_memory_usage,
	formatReadableSize(sum(memory_usage)) as p_total_memory_usage
from clusterAllReplicas(_CLUSTER_NAME, system.query_log)
where
	exception_code = 0 and
	query_start_time > now() - interval 3 day and
	type = 'QueryFinish'
group by _shard_num, host_name, current_database
order by _shard_num, host_name, current_database
limit 30;