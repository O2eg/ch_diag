-- subquery to avoid "Cannot find column _shard_num in source stream"
select
	_shard_num,
	host_name,
	count(1) as query_times,
	sum(read_rows) as total_read_rows,
	sum(read_bytes) as total_read_bytes,
	formatReadableSize(sum(read_bytes)) as p_read_bytes,
	sum(result_rows) as total_result_rows,
	sum(result_bytes) as total_result_bytes,
	formatReadableSize(sum(result_bytes)) as p_total_result_bytes,
	sum(memory_usage) as total_memory_usage,
	formatReadableSize(sum(memory_usage)) as p_total_memory_usage
from (
	select
		_shard_num,
		hostName() as host_name,
		read_rows,
		read_bytes,
		result_rows,
		result_bytes,
		memory_usage
	from clusterAllReplicas(test_cluster, system.query_log)
	where
		exception_code = 0 and
		query_start_time > now() - interval 3 day and
		type = 'QueryFinish'
) t
group by _shard_num, host_name
order by _shard_num, host_name
limit 30;